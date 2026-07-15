from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from .crud import crud_customers
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
        return customer

    async def create(self, db: AsyncSession, customer_in: CustomerCreate) -> dict[str, Any]:
        customer = await crud_customers.create(db=db, object=customer_in, commit=False)
        await db.commit()
        return await self.get_by_id(db, customer["id"])

    async def update(self, db: AsyncSession, customer_id: UUID, customer_in: CustomerUpdate) -> dict[str, Any]:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")

        customer_data = customer_in.model_dump(exclude_unset=True)
        await crud_customers.update(db=db, object=customer_data, id=customer_id, commit=False)
        await db.commit()
        return await self.get_by_id(db, customer_id)

    async def delete(self, db: AsyncSession, customer_id: UUID) -> None:
        customer = await crud_customers.get(db=db, id=customer_id, deleted=False)
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID {customer_id} not found")
        await crud_customers.delete(db=db, id=customer_id)
        await db.commit()


customer_service = CustomerService()
