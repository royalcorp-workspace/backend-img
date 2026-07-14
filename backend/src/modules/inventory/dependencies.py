from typing import Annotated

from fastapi import Depends

from .service import InventoryService


def get_inventory_service() -> InventoryService:
    return InventoryService()


InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
