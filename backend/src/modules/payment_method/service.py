from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_payment_methods
from .schemas import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate

logger = get_logger()


class PaymentMethodService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_payment_methods.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=PaymentMethodRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, method_id: int) -> dict[str, Any]:
        method = await crud_payment_methods.get(db=db, id=method_id, is_deleted=False)
        if not method:
            raise ResourceNotFoundError(f"Payment method with ID {method_id} not found")
        return method

    async def create(self, db: AsyncSession, method_in: PaymentMethodCreate) -> dict[str, Any]:
        existing = await crud_payment_methods.get(db=db, code=method_in.code)
        if existing:
            raise ResourceExistsError(f"Payment method with code '{method_in.code}' already exists")
        res = await crud_payment_methods.create(db=db, object=method_in)
        await db.commit()
        return res

    async def update(self, db: AsyncSession, method_id: int, method_in: PaymentMethodUpdate) -> dict[str, Any]:
        method = await crud_payment_methods.get(db=db, id=method_id, is_deleted=False)
        if not method:
            raise ResourceNotFoundError(f"Payment method with ID {method_id} not found")
        if method_in.code and method_in.code != method.get("code"):
            existing = await crud_payment_methods.get(db=db, code=method_in.code)
            if existing:
                raise ResourceExistsError(f"Payment method with code '{method_in.code}' already exists")
        res = await crud_payment_methods.update(db=db, object=method_in, id=method_id)
        await db.commit()
        return res

    async def delete(self, db: AsyncSession, method_id: int) -> None:
        method = await crud_payment_methods.get(db=db, id=method_id, is_deleted=False)
        if not method:
            raise ResourceNotFoundError(f"Payment method with ID {method_id} not found")
        await crud_payment_methods.delete(db=db, id=method_id)
        await db.commit()


payment_method_service = PaymentMethodService()
