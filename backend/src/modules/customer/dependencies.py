from typing import Annotated

from fastapi import Depends

from .service import CustomerService


def get_customer_service() -> CustomerService:
    return CustomerService()


CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]
