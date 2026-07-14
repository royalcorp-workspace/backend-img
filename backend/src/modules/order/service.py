from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from .crud import crud_orders
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderRead, OrderUpdate

logger = get_logger()


class OrderService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        return await crud_orders.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=OrderRead, **filters
        )

    async def get_by_id(self, db: AsyncSession, order_id: int) -> dict[str, Any]:
        order = await crud_orders.get(db=db, id=order_id, is_deleted=False)
        if not order:
            raise ResourceNotFoundError(f"Order with ID {order_id} not found")
        return order

    async def create(self, db: AsyncSession, order_in: OrderCreate) -> Any:
        order_data = order_in.model_dump(exclude={"items"})
        order = Order(**order_data)
        db.add(order)
        await db.flush()  # Populate order.id

        # Insert items
        for item_in in order_in.items:
            item_data = item_in.model_dump()
            order_item = OrderItem(order_id=order.id, **item_data)
            db.add(order_item)

        await db.commit()
        # Reload order with relations
        order_db = await crud_orders.get(db=db, id=order.id, is_deleted=False)
        return order_db

    async def update(self, db: AsyncSession, order_id: int, order_in: OrderUpdate) -> Any:
        order = await crud_orders.get(db=db, id=order_id, is_deleted=False)
        if not order:
            raise ResourceNotFoundError(f"Order with ID {order_id} not found")
        
        # We don't support updating nested items directly in this basic update
        update_data = order_in.model_dump(exclude_unset=True)
        updated_order = await crud_orders.update(db=db, db_obj=order, obj_in=update_data)
        await db.commit()
        return updated_order

    async def delete(self, db: AsyncSession, order_id: int) -> None:
        order = await crud_orders.get(db=db, id=order_id, is_deleted=False)
        if not order:
            raise ResourceNotFoundError(f"Order with ID {order_id} not found")
        await crud_orders.delete(db=db, id=order_id)
        await db.commit()


order_service = OrderService()
