import re
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from ..common.utils import get_media_url
from ..region.models import City, Province, SubDistrict
from .crud import crud_customers
from .models import Address, Customer
from .schemas import AddressCreate, CustomerCreate, CustomerProfileUpdate, CustomerRead, CustomerUpdate

logger = get_logger()


async def _fetch_and_enrich_addresses_for_customer(
    db: AsyncSession, customer_id: UUID, user_id: UUID | None = None
) -> list[dict[str, Any]]:
    conditions = [Address.customer_id == customer_id]
    if user_id:
        conditions.append(Address.user_id == user_id)

    result = await db.execute(
        select(Address)
        .where(or_(*conditions), Address.deleted == False)
        .order_by(Address.is_primary.desc(), Address.created_at.asc())
    )
    address_objs = result.scalars().all()
    if not address_objs:
        return []

    city_ids = {a.city_id for a in address_objs if a.city_id}
    sub_district_ids = {a.sub_district_id for a in address_objs if a.sub_district_id}

    city_map: dict[UUID, City] = {}
    if city_ids:
        city_res = await db.execute(select(City).where(City.id.in_(city_ids), City.deleted == False))
        for c in city_res.scalars().all():
            city_map[c.id] = c

    sub_dist_map: dict[UUID, SubDistrict] = {}
    if sub_district_ids:
        sub_dist_res = await db.execute(
            select(SubDistrict).where(SubDistrict.id.in_(sub_district_ids), SubDistrict.deleted == False)
        )
        for sd in sub_dist_res.scalars().all():
            sub_dist_map[sd.id] = sd

    province_map: dict[str, str] = {}
    province_ids_to_fetch: set[UUID] = set()
    for sd in sub_dist_map.values():
        if sd.province_id:
            try:
                province_ids_to_fetch.add(UUID(str(sd.province_id)))
            except (ValueError, TypeError):
                pass
    for c in city_map.values():
        if c.province_id:
            try:
                province_ids_to_fetch.add(UUID(str(c.province_id)))
            except (ValueError, TypeError):
                pass

    if province_ids_to_fetch:
        prov_res = await db.execute(select(Province).where(Province.id.in_(province_ids_to_fetch), Province.deleted == False))
        for p in prov_res.scalars().all():
            province_map[str(p.id)] = p.name

    addresses = []
    for a in address_objs:
        sub_dist = sub_dist_map.get(a.sub_district_id) if a.sub_district_id else None
        city = city_map.get(a.city_id) if a.city_id else None

        sub_district_name = sub_dist.sub_district if sub_dist else None
        district_name = sub_dist.district if sub_dist else None
        city_name = city.name if city else None

        province_id_raw = (
            sub_dist.province_id
            if sub_dist and sub_dist.province_id
            else (city.province_id if city and city.province_id else None)
        )
        province_name = (
            (sub_dist.province if sub_dist and sub_dist.province else None)
            or (city.province if city and city.province else None)
            or (province_map.get(str(province_id_raw)) if province_id_raw else None)
        )
        postal_code = a.postal_code or (sub_dist.postal_code if sub_dist else None)

        addresses.append(
            {
                "id": a.id,
                "customer_id": a.customer_id,
                "user_id": a.user_id,
                "label": a.label,
                "recipient_name": a.recipient_name,
                "phone": a.phone,
                "address": a.address,
                "city_id": a.city_id,
                "city_name": city_name,
                "sub_district_id": a.sub_district_id,
                "sub_district_name": sub_district_name,
                "district_name": district_name,
                "province_id": str(province_id_raw) if province_id_raw else None,
                "province_name": province_name,
                "postal_code": postal_code,
                "is_primary": a.is_primary,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
        )
    return addresses


class CustomerService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters) -> dict[str, Any]:
        data = await crud_customers.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=CustomerRead, **filters
        )
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            for cust in data["data"]:
                c_id = cust.get("id") if isinstance(cust, dict) else getattr(cust, "id", None)
                u_id = cust.get("user_id") if isinstance(cust, dict) else getattr(cust, "user_id", None)
                if c_id:
                    addrs = await _fetch_and_enrich_addresses_for_customer(db, c_id, u_id)
                    if isinstance(cust, dict):
                        cust["addresses"] = addrs
                    else:
                        setattr(cust, "addresses", addrs)
        return data

    async def get_by_id(self, db: AsyncSession, customer_id: UUID) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        user_id = customer.get("user_id")
        customer["addresses"] = await _fetch_and_enrich_addresses_for_customer(db, customer_id, user_id)

        avatar_url = None
        if user_id:
            from ..user.models import User
            u_res = await db.execute(select(User).where(User.id == user_id))
            user_obj = u_res.scalar_one_or_none()
            if user_obj:
                raw_avatar = user_obj.avatar or user_obj.photo_url
                if raw_avatar:
                    avatar_url = get_media_url(raw_avatar)
        if not avatar_url and customer.get("meta"):
            try:
                import json
                meta_dict = json.loads(customer["meta"]) if isinstance(customer["meta"], str) else customer["meta"]
                if isinstance(meta_dict, dict) and meta_dict.get("avatar"):
                    avatar_url = get_media_url(meta_dict["avatar"])
            except Exception:
                pass

        customer["avatar"] = avatar_url
        customer["photo_url"] = avatar_url
        return customer

    async def create(self, db: AsyncSession, customer_in: CustomerCreate) -> dict[str, Any]:
        customer_data = customer_in.model_dump(exclude={"addresses"})
        email = customer_data.get("email")
        existing = None
        if email:
            clean_email = email.strip().lower()
            stmt = select(Customer).where(func.lower(Customer.email) == clean_email, Customer.deleted == False)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()

        if existing:
            if customer_data.get("name"):
                existing.name = customer_data["name"]
            if customer_data.get("phone"):
                existing.phone = customer_data["phone"]
            if customer_data.get("user_id") and not existing.user_id:
                existing.user_id = customer_data["user_id"]
            db.add(existing)
            cust_id = existing.id
            user_id = existing.user_id
        else:
            customer = await crud_customers.create(db=db, object=customer_data, commit=False)
            cust_id = customer.get("id") if isinstance(customer, dict) else customer.id
            user_id = customer_data.get("user_id")

        if customer_in.addresses:
            for addr_in in customer_in.addresses:
                addr_data = addr_in.model_dump(exclude_unset=True)
                addr_data["user_id"] = user_id
                addr_data["customer_id"] = cust_id
                address_obj = Address(**addr_data)
                db.add(address_obj)

        await db.commit()
        return await self.get_by_id(db, cust_id)

    async def update(self, db: AsyncSession, customer_id: UUID, customer_in: CustomerUpdate) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        customer_data = customer_in.model_dump(
            exclude_unset=True,
            exclude={"addresses", "address", "addresses_id", "address_id"},
        )
        if customer_data:
            await crud_customers.update(db=db, object=customer_data, id=customer_id, commit=False)

        user_id = customer.get("user_id") or customer_data.get("user_id")

        # Collect addresses to process
        address_items: list[dict[str, Any]] = []
        if customer_in.addresses is not None:
            for item in customer_in.addresses:
                address_items.append(item.model_dump(exclude_unset=True))
        elif customer_in.address is not None:
            address_items.append(customer_in.address.model_dump(exclude_unset=True))
        elif customer_in.addresses_id or customer_in.address_id:
            addr_id_val = customer_in.addresses_id or customer_in.address_id
            address_items.append({"id": addr_id_val})

        for addr_payload in address_items:
            target_addr_id = (
                addr_payload.get("id")
                or addr_payload.get("address_id")
                or addr_payload.get("addresses_id")
                or customer_in.addresses_id
                or customer_in.address_id
            )

            # If addresses_id/id is present, update the existing address
            if target_addr_id:
                res_addr = await db.execute(
                    select(Address).where(Address.id == target_addr_id, Address.deleted == False)
                )
                existing_addr = res_addr.scalar_one_or_none()
                if not existing_addr:
                    raise ResourceNotFoundError(f"Address with ID {target_addr_id} not found")

                if addr_payload.get("is_primary"):
                    conditions = [Address.customer_id == customer_id]
                    if user_id:
                        conditions.append(Address.user_id == user_id)
                    await db.execute(
                        update(Address)
                        .where(or_(*conditions), Address.deleted == False)
                        .values(is_primary=False)
                    )

                for field, val in addr_payload.items():
                    if field in ("id", "address_id", "addresses_id"):
                        continue
                    if hasattr(existing_addr, field) and val is not None:
                        setattr(existing_addr, field, val)
            else:
                # If no ID provided, insert as new address
                if addr_payload.get("is_primary"):
                    conditions = [Address.customer_id == customer_id]
                    if user_id:
                        conditions.append(Address.user_id == user_id)
                    await db.execute(
                        update(Address)
                        .where(or_(*conditions), Address.deleted == False)
                        .values(is_primary=False)
                    )

                addr_clean = {k: v for k, v in addr_payload.items() if k not in ("id", "address_id", "addresses_id")}
                addr_clean["customer_id"] = customer_id
                addr_clean["user_id"] = user_id
                new_address = Address(**addr_clean)
                db.add(new_address)

        await db.commit()
        return await self.get_by_id(db, customer_id)

    async def add_address(self, db: AsyncSession, customer_id: UUID, address_in: AddressCreate) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        user_id = customer.get("user_id")

        if address_in.is_primary:
            conditions = [Address.customer_id == customer_id]
            if user_id:
                conditions.append(Address.user_id == user_id)
            await db.execute(
                update(Address)
                .where(or_(*conditions), Address.deleted == False)
                .values(is_primary=False)
            )

        addr_data = address_in.model_dump(exclude_unset=True)
        addr_data["customer_id"] = customer_id
        addr_data["user_id"] = user_id
        address_obj = Address(**addr_data)
        db.add(address_obj)

        await db.commit()
        return await self.get_by_id(db, customer_id)

    async def set_primary_address(self, db: AsyncSession, customer_id: UUID, address_id: UUID) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        user_id = customer.get("user_id")

        # Verify address exists for this customer or user
        conditions = [Address.customer_id == customer_id]
        if user_id:
            conditions.append(Address.user_id == user_id)

        result = await db.execute(
            select(Address).where(Address.id == address_id, or_(*conditions), Address.deleted == False)
        )
        address = result.scalar_one_or_none()
        if not address:
            raise ResourceNotFoundError(f"Address with ID {address_id} not found for this customer")

        # Reset all addresses for this customer/user to is_primary = False
        await db.execute(
            update(Address)
            .where(or_(*conditions), Address.deleted == False)
            .values(is_primary=False)
        )

        # Set selected address to primary
        await db.execute(
            update(Address)
            .where(Address.id == address_id)
            .values(is_primary=True)
        )

        await db.commit()
        return await self.get_by_id(db, customer_id)

    async def get_or_create_for_user(
        self, db: AsyncSession, user_id: UUID, user_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Fetch or automatically create customer record for the authenticated user."""
        email = user_data.get("email")
        conditions = [Customer.user_id == user_id]
        if email:
            conditions.append(Customer.email == email)

        stmt = select(Customer).where(or_(*conditions), Customer.deleted == False)
        res = await db.execute(stmt)
        customer = res.scalar_one_or_none()

        if not customer:
            customer = Customer(
                name=user_data.get("name") or (email.split("@")[0] if email else "Customer"),
                email=email,
                phone=user_data.get("phone"),
                user_id=user_id,
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
        elif not customer.user_id:
            customer.user_id = user_id
            db.add(customer)
            await db.commit()

        return await self.get_by_id(db, customer.id)

    async def update_profile_for_user(
        self, db: AsyncSession, user_id: UUID, customer_in: CustomerProfileUpdate | CustomerUpdate, user_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update customer profile (identity, avatar, password) for authenticated user without modifying addresses."""
        from ...infrastructure.auth.http_exceptions import HTTPException
        from crudauth.utils import get_password_hash, verify_password
        from ..user.models import User

        # Fetch User entity
        u_res = await db.execute(select(User).where(User.id == user_id))
        user_obj = u_res.scalar_one_or_none()
        if not user_obj:
            raise ResourceNotFoundError("User not found")

        email = user_data.get("email") or user_obj.email
        conditions = [Customer.user_id == user_id]
        if email:
            conditions.append(Customer.email == email)

        stmt = select(Customer).where(or_(*conditions), Customer.deleted == False)
        res = await db.execute(stmt)
        customer = res.scalar_one_or_none()

        if not customer:
            customer = Customer(
                name=customer_in.name or user_obj.name or (email.split("@")[0] if email else "Customer"),
                email=customer_in.email or email,
                phone=customer_in.phone or user_obj.phone,
                user_id=user_id,
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
        elif not customer.user_id:
            customer.user_id = user_id
            db.add(customer)
            await db.commit()

        # Handle Password Change / Reset if requested
        new_pw = getattr(customer_in, "new_password", None) or getattr(customer_in, "password", None)
        if new_pw and str(new_pw).strip():
            new_pw = str(new_pw).strip()
            confirm_pw = getattr(customer_in, "confirm_password", None) or getattr(customer_in, "password_confirmation", None)
            if confirm_pw and str(confirm_pw).strip() != new_pw:
                raise HTTPException(status_code=400, detail="Konfirmasi password baru tidak cocok.")

            # Validate strong password: min 8, lower, upper, digit, symbol
            if len(new_pw) < 8:
                raise HTTPException(status_code=400, detail="Password minimal harus 8 karakter.")
            if not re.search(r"[a-z]", new_pw):
                raise HTTPException(status_code=400, detail="Password harus mengandung setidaknya 1 huruf kecil.")
            if not re.search(r"[A-Z]", new_pw):
                raise HTTPException(status_code=400, detail="Password harus mengandung setidaknya 1 huruf besar.")
            if not re.search(r"[0-9]", new_pw):
                raise HTTPException(status_code=400, detail="Password harus mengandung setidaknya 1 angka.")
            if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-+=_\[\]\\\/~`]", new_pw):
                raise HTTPException(status_code=400, detail="Password harus mengandung setidaknya 1 simbol karakter khusus (contoh: @, #, $, !).")

            # If user already has a password, verify current password
            if user_obj.password and user_obj.password.strip():
                curr_pw = getattr(customer_in, "current_password", None) or getattr(customer_in, "old_password", None)
                if not curr_pw:
                    raise HTTPException(status_code=400, detail="Password saat ini diperlukan untuk mengubah password.")
                if not verify_password(curr_pw, user_obj.password):
                    raise HTTPException(status_code=400, detail="Password saat ini tidak sesuai.")

            user_obj.password = get_password_hash(new_pw)

        # Handle Avatar
        avatar_val = getattr(customer_in, "avatar", None) or getattr(customer_in, "photo_url", None)
        if avatar_val is not None:
            user_obj.avatar = avatar_val
            user_obj.photo_url = avatar_val
            import json
            meta_dict = {}
            if customer.meta:
                try:
                    meta_dict = json.loads(customer.meta) if isinstance(customer.meta, str) else dict(customer.meta)
                except Exception:
                    meta_dict = {}
            meta_dict["avatar"] = avatar_val
            customer.meta = json.dumps(meta_dict)

        # Handle Identity fields (Strictly identity only, NO address modifications)
        if customer_in.name:
            user_obj.name = customer_in.name
            customer.name = customer_in.name
        if customer_in.phone:
            user_obj.phone = customer_in.phone
            customer.phone = customer_in.phone
        if getattr(customer_in, "email", None):
            user_obj.email = customer_in.email
            customer.email = customer_in.email

        db.add(user_obj)
        db.add(customer)
        await db.commit()

        return await self.get_by_id(db, customer.id)


customer_service = CustomerService()

