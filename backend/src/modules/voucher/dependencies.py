from typing import Annotated

from fastapi import Depends

from .service import VoucherService


def get_voucher_service() -> VoucherService:
    return VoucherService()


VoucherServiceDep = Annotated[VoucherService, Depends(get_voucher_service)]
