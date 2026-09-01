from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from .crud import crud_customers
from .models import Address
from .schemas import CustomerCreate, CustomerRead, CustomerUpdate

logger = get_logger()


class CustomerService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_customers.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=CustomerRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, customer_id: UUID) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")
            
        # Fetch associated addresses via user_id
        user_id = customer.get("user_id")
        addresses = []
        if user_id:
            result = await db.execute(select(Address).where(Address.user_id == user_id, Address.deleted == False))
            address_objs = result.scalars().all()
            addresses = [
                {
                    "id": a.id,
                    "city_id": a.city_id,
                    "label": a.label,
                    "recipient_name": a.recipient_name,
                    "phone": a.phone,
                    "address": a.address,
                    "user_id": a.user_id,
                    "sub_district_id": a.sub_district_id,
                    "postal_code": a.postal_code,
                    "is_primary": a.is_primary,
                }
                for a in address_objs
            ]
        
        customer["addresses"] = addresses
        return customer

    async def create(self, db: AsyncSession, customer_in: CustomerCreate) -> dict[str, Any]:
        # Exclude addresses from fastcrud payload
        customer_data = customer_in.model_dump(exclude={"addresses"})
        customer = await crud_customers.create(db=db, object=customer_data, commit=False)
        
        # Determine the user_id (either passed in or we use customer id... usually user_id is passed)
        user_id = customer_data.get("user_id")
        
        if customer_in.addresses:
            for addr_in in customer_in.addresses:
                addr_data = addr_in.model_dump()
                addr_data["user_id"] = user_id
                addr_data["customer_id"] = customer.get("id") if isinstance(customer, dict) else customer.id
                address_obj = Address(**addr_data)
                db.add(address_obj)
        
        await db.commit()
        return await self.get_by_id(db, customer.get("id") if isinstance(customer, dict) else customer.id)

    async def update(self, db: AsyncSession, customer_id: UUID, customer_in: CustomerUpdate) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        customer_data = customer_in.model_dump(exclude_unset=True, exclude={"addresses"})
        if customer_data:
            await crud_customers.update(db=db, object=customer_data, id=customer_id, commit=False)
            
        user_id = customer.get("user_id") or customer_data.get("user_id")
        
        # Optionally insert new addresses on update
        if getattr(customer_in, "addresses", None):
            for addr_in in customer_in.addresses:
                addr_data = addr_in.model_dump()
                addr_data["user_id"] = user_id
                addr_data["customer_id"] = customer_id
                address_obj = Address(**addr_data)
                db.add(address_obj)
                
        await db.commit()
        return await self.get_by_id(db, customer_id)




    async def set_primary_address(self, db: AsyncSession, customer_id: UUID, address_id: UUID) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        user_id = customer.get("user_id")
        if not user_id:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} has no associated user account")

        # Verify address exists for this user
        result = await db.execute(select(Address).where(Address.id == address_id, Address.user_id == user_id, Address.deleted.is_(False)))
        address = result.scalar_one_or_none()
        if not address:
            raise ResourceNotFoundError(f"Address with ID {address_id} not found for this customer")

        # Reset all addresses for this user to is_primary = False
        await db.execute(
            update(Address)
            .where(Address.user_id == user_id, Address.deleted.is_(False))
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


customer_service = CustomerService()
