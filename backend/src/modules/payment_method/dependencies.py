from typing import Annotated

from fastapi import Depends

from .service import PaymentMethodService, payment_method_service


def get_payment_method_service() -> PaymentMethodService:
    return payment_method_service


PaymentMethodServiceDep = Annotated[PaymentMethodService, Depends(get_payment_method_service)]
