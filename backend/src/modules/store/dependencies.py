from typing import Annotated

from fastapi import Depends

from .service import StoreService, store_service


def get_store_service() -> StoreService:
    return store_service


StoreServiceDep = Annotated[StoreService, Depends(get_store_service)]
