from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_couriers, crud_shipping_addresses
from .schemas import (
    CourierCreate,
    CourierRead,
    CourierUpdate,
    ShippingAddressCreate,
    ShippingAddressRead,
    ShippingAddressUpdate,
)

logger = get_logger()


class CourierService:
    # --- Courier ---
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_couriers.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=CourierRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, courier_id: int) -> dict[str, Any]:
        courier = await crud_couriers.get(db=db, id=courier_id, is_deleted=False)
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

    async def update(self, db: AsyncSession, courier_id: int, courier_in: CourierUpdate) -> dict[str, Any]:
        courier = await crud_couriers.get(db=db, id=courier_id, is_deleted=False)
        if not courier:
            raise ResourceNotFoundError(f"Courier with ID {courier_id} not found")
        if courier_in.code and courier_in.code != courier.get("code"):
            existing = await crud_couriers.get(db=db, code=courier_in.code)
            if existing:
                raise ResourceExistsError(f"Courier with code '{courier_in.code}' already exists")
        res = await crud_couriers.update(db=db, object=courier_in, id=courier_id)
        await db.commit()
        return res

    async def delete(self, db: AsyncSession, courier_id: int) -> None:
        courier = await crud_couriers.get(db=db, id=courier_id, is_deleted=False)
        if not courier:
            raise ResourceNotFoundError(f"Courier with ID {courier_id} not found")
        await crud_couriers.delete(db=db, id=courier_id)
        await db.commit()

    # --- Shipping Address (Rates) ---
    async def get_shipping_addresses_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_shipping_addresses.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=ShippingAddressRead, **filters
        )

    async def get_shipping_address_by_id(self, db: AsyncSession, address_id: int) -> dict[str, Any]:
        res = await crud_shipping_addresses.get(db=db, id=address_id, is_deleted=False)
        if not res:
            raise ResourceNotFoundError(f"Shipping address with ID {address_id} not found")
        return res

    async def create_shipping_address(self, db: AsyncSession, address_in: ShippingAddressCreate) -> dict[str, Any]:
        # Validate Courier exists
        courier = await crud_couriers.get(db=db, id=address_in.courier_id, is_deleted=False)
        if not courier:
            raise ResourceNotFoundError(f"Courier with ID {address_in.courier_id} not found")

        res = await crud_shipping_addresses.create(db=db, object=address_in)
        await db.commit()
        return res

    async def update_shipping_address(
        self, db: AsyncSession, address_id: int, address_in: ShippingAddressUpdate
    ) -> dict[str, Any]:
        addr = await crud_shipping_addresses.get(db=db, id=address_id, is_deleted=False)
        if not addr:
            raise ResourceNotFoundError(f"Shipping address with ID {address_id} not found")

        if address_in.courier_id:
            courier = await crud_couriers.get(db=db, id=address_in.courier_id, is_deleted=False)
            if not courier:
                raise ResourceNotFoundError(f"Courier with ID {address_in.courier_id} not found")

        res = await crud_shipping_addresses.update(db=db, object=address_in, id=address_id)
        await db.commit()
        return res

    async def delete_shipping_address(self, db: AsyncSession, address_id: int) -> None:
        addr = await crud_shipping_addresses.get(db=db, id=address_id, is_deleted=False)
        if not addr:
            raise ResourceNotFoundError(f"Shipping address with ID {address_id} not found")
        await crud_shipping_addresses.delete(db=db, id=address_id)
        await db.commit()


courier_service = CourierService()
