from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..product.crud import crud_products
from ..product.schemas import ProductCreate, ProductRead


class InventoryService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        result = await crud_products.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=ProductRead, **filters
        )
        return {
            "data": [{"id": p["id"], "name": p["name"], "stock_qty": 0} for p in result.get("data", [])],
            "count": result.get("count", 0),
        }

    async def create(self, db: AsyncSession, product_in: ProductCreate) -> dict[str, Any]:
        product = await crud_products.create(db=db, object=product_in)
        return {"id": product["id"], "name": product["name"]}


inventory_service = InventoryService()
