from typing import Annotated

from fastapi import Depends

from .service import CourierService, courier_service


def get_courier_service() -> CourierService:
    return courier_service


CourierServiceDep = Annotated[CourierService, Depends(get_courier_service)]
