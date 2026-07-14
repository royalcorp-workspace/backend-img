from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from .crud import crud_addresses, crud_customers
from .schemas import CustomerCreate, CustomerRead, CustomerUpdate

logger = get_logger()


class CustomerService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_customers.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=CustomerRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, customer_id: int) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, is_deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")
        return customer

    async def create(self, db: AsyncSession, customer_in: CustomerCreate) -> dict[str, Any]:
        addresses_in = customer_in.addresses
        customer_data = customer_in.model_dump(exclude={"addresses"})

        customer = await crud_customers.create(db=db, object=customer_data, commit=False)
        await db.flush()

        for addr in addresses_in:
            addr_data = addr.model_dump()
            addr_data["customer_id"] = customer["id"]
            await crud_addresses.create(db=db, object=addr_data, commit=False)

        await db.commit()
        return await self.get_by_id(db, customer["id"])

    async def update(self, db: AsyncSession, customer_id: int, customer_in: CustomerUpdate) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, is_deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        addresses_in = customer_in.addresses
        customer_data = customer_in.model_dump(exclude={"addresses"}, exclude_unset=True)

        await crud_customers.update(db=db, object=customer_data, id=customer_id, commit=False)

        if addresses_in is not None:
            existing_addresses = await crud_addresses.get_multi(db=db, customer_id=customer_id, limit=100)
            for addr in existing_addresses.get("data", []):
                await crud_addresses.delete(db=db, id=addr["id"], commit=False)

            for addr in addresses_in:
                addr_data = addr.model_dump()
                addr_data["customer_id"] = customer_id
                await crud_addresses.create(db=db, object=addr_data, commit=False)

        await db.commit()
        return await self.get_by_id(db, customer_id)

    async def delete(self, db: AsyncSession, customer_id: int) -> None:
        customer = await crud_customers.get(db=db, id=customer_id, is_deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")
        await crud_customers.delete(db=db, id=customer_id)
        await db.commit()


customer_service = CustomerService()
