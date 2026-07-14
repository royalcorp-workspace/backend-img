from typing import Annotated

from fastapi import Depends

from .service import OrderService


def get_order_service() -> OrderService:
    return OrderService()


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
