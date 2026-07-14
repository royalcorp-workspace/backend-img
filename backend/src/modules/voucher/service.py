from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_vouchers
from .schemas import VoucherCreate, VoucherRead, VoucherUpdate

logger = get_logger()


class VoucherService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_vouchers.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=VoucherRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, voucher_id: int) -> dict[str, Any]:
        voucher = await crud_vouchers.get(db=db, id=voucher_id, is_deleted=False)
        if not voucher:
            raise ResourceNotFoundError(f"Voucher with ID {voucher_id} not found")
        return voucher

    async def create(self, db: AsyncSession, voucher_in: VoucherCreate) -> dict[str, Any]:
        existing = await crud_vouchers.get(db=db, code=voucher_in.code)
        if existing:
            raise ResourceExistsError(f"Voucher with code '{voucher_in.code}' already exists")
        return await crud_vouchers.create(db=db, object=voucher_in)

    async def update(self, db: AsyncSession, voucher_id: int, voucher_in: VoucherUpdate) -> dict[str, Any]:
        voucher = await crud_vouchers.get(db=db, id=voucher_id, is_deleted=False)
        if not voucher:
            raise ResourceNotFoundError(f"Voucher with ID {voucher_id} not found")
        if voucher_in.code and voucher_in.code != voucher.get("code"):
            existing = await crud_vouchers.get(db=db, code=voucher_in.code)
            if existing:
                raise ResourceExistsError(f"Voucher with code '{voucher_in.code}' already exists")
        return await crud_vouchers.update(db=db, object=voucher_in, id=voucher_id)

    async def delete(self, db: AsyncSession, voucher_id: int) -> None:
        voucher = await crud_vouchers.get(db=db, id=voucher_id, is_deleted=False)
        if not voucher:
            raise ResourceNotFoundError(f"Voucher with ID {voucher_id} not found")
        await crud_vouchers.delete(db=db, id=voucher_id)


voucher_service = VoucherService()
