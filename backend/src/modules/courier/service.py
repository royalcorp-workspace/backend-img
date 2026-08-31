from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_couriers, crud_shipping_addresses
from .models import Courier, ShippingAddress
from .schemas import (
    CourierCreate,
    CourierRead,
    CourierUpdate,
    ShippingAddressCreate,
    ShippingAddressRead,
    ShippingAddressUpdate,
)

logger = get_logger()


def _shipping_address_to_dict(addr: ShippingAddress) -> dict[str, Any]:
    mapping = {1: "reguler", 2: "express", 3: "same-day"}
    type_name = mapping.get(addr.type) if addr.type else None

    return {
        "id": addr.id,
        "courier_id": addr.courier_id,
        "sub_district_id": addr.sub_district_id,
        "type": addr.type,
        "type_name": type_name,
        "price": addr.price,
        "is_active": addr.is_active,
        "sort_order": addr.sort_order,
        "created_at": addr.created_at,
        "updated_at": addr.updated_at,
        "deleted": addr.deleted,
        "creator": addr.creator,
        "editor": addr.editor,
        "courier": {
            "id": addr.courier.id,
            "code": addr.courier.code,
            "name": addr.courier.name,
            "type": addr.courier.type,
            "is_active": addr.courier.is_active,
            "sort_order": addr.courier.sort_order,
        }
        if addr.courier
        else None,
    }


class CourierService:
    # --- Courier ---
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_couriers.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=CourierRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, courier_id: UUID) -> dict[str, Any]:
        courier = await crud_couriers.get(db=db, id=courier_id, deleted=False)
        if not courier:
            raise ResourceNotFoundError(f"Courier with ID {courier_id} not found")
        return courier

    async def create(self, db: AsyncSession, courier_in: CourierCreate) -> dict[str, Any]:
        existing = await crud_couriers.get(db=db, code=courier_in.code)
        if existing:
            raise ResourceExistsError(f"Courier with code '{courier_in.code}' already exists")
        res = await crud_couriers.create(db=db, object=courier_in)
        await db.commit()
        return res

    async def update(self, db: AsyncSession, courier_id: UUID, courier_in: CourierUpdate) -> dict[str, Any]:
        courier = await crud_couriers.get(db=db, id=courier_id, deleted=False)
        if not courier:
            raise ResourceNotFoundError(f"Courier with ID {courier_id} not found")
        if courier_in.code and courier_in.code != courier.get("code"):
            existing = await crud_couriers.get(db=db, code=courier_in.code)
            if existing:
                raise ResourceExistsError(f"Courier with code '{courier_in.code}' already exists")
        res = await crud_couriers.update(db=db, object=courier_in, id=courier_id)
        await db.commit()
        return res

    async def delete(self, db: AsyncSession, courier_id: UUID) -> None:
        courier = await crud_couriers.get(db=db, id=courier_id, deleted=False)
        if not courier:
            raise ResourceNotFoundError(f"Courier with ID {courier_id} not found")
        await crud_couriers.delete(db=db, id=courier_id)
        await db.commit()

    # --- Shipping Address (Rates) ---
    async def get_shipping_addresses_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        query = (
            select(ShippingAddress)
            .options(selectinload(ShippingAddress.courier))
            .where(ShippingAddress.deleted.is_(False))
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(ShippingAddress).where(ShippingAddress.deleted.is_(False))

        for key, value in filters.items():
            if hasattr(ShippingAddress, key):
                query = query.where(getattr(ShippingAddress, key) == value)
                count_query = count_query.where(getattr(ShippingAddress, key) == value)

        result = await db.execute(query)
        addresses = result.scalars().all()
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        return {
            "data": [_shipping_address_to_dict(addr) for addr in addresses],
            "total_count": total,
        }

    async def get_shipping_address_by_id(self, db: AsyncSession, address_id: UUID) -> dict[str, Any]:
        query = (
            select(ShippingAddress)
            .options(selectinload(ShippingAddress.courier))
            .where(ShippingAddress.id == address_id, ShippingAddress.deleted.is_(False))
        )
        result = await db.execute(query)
        addr = result.scalar_one_or_none()
        if not addr:
            raise ResourceNotFoundError(f"Shipping address with ID {address_id} not found")
        return _shipping_address_to_dict(addr)

    async def create_shipping_address(self, db: AsyncSession, address_in: ShippingAddressCreate) -> dict[str, Any]:
        courier = await crud_couriers.get(db=db, id=address_in.courier_id, deleted=False)
        if not courier:
            raise ResourceNotFoundError(f"Courier with ID {address_in.courier_id} not found")

        res = await crud_shipping_addresses.create(db=db, object=address_in)
        await db.commit()
        return res

    async def update_shipping_address(
        self, db: AsyncSession, address_id: UUID, address_in: ShippingAddressUpdate
    ) -> dict[str, Any]:
        addr = await crud_shipping_addresses.get(db=db, id=address_id, deleted=False)
        if not addr:
            raise ResourceNotFoundError(f"Shipping address with ID {address_id} not found")

        if address_in.courier_id:
            courier = await crud_couriers.get(db=db, id=address_in.courier_id, deleted=False)
            if not courier:
                raise ResourceNotFoundError(f"Courier with ID {address_in.courier_id} not found")

        res = await crud_shipping_addresses.update(db=db, object=address_in, id=address_id)
        await db.commit()
        return res

    async def delete_shipping_address(self, db: AsyncSession, address_id: UUID) -> None:
        addr = await crud_shipping_addresses.get(db=db, id=address_id, deleted=False)
        if not addr:
            raise ResourceNotFoundError(f"Shipping address with ID {address_id} not found")
        await crud_shipping_addresses.delete(db=db, id=address_id)
        await db.commit()


courier_service = CourierService()
