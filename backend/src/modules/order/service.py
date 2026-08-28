from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from .crud import crud_orders
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderUpdate

logger = get_logger()


def _order_to_dict(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "subtotal": order.subtotal,
        "tax": order.tax,
        "discount": order.discount,
        "total": order.total,
        "notes": order.notes,
        "meta": order.meta,
        "creator": order.creator,
        "editor": order.editor,
        "deleted": order.deleted,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "customer": {
            "id": order.customer.id,
            "name": order.customer.name,
            "email": order.customer.email,
            "phone": order.customer.phone,
            "user_id": order.customer.user_id,
            "created_at": order.customer.created_at,
            "updated_at": order.customer.updated_at,
            "deleted": order.customer.deleted,
        } if order.customer else None,
        "items": [
            {
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "product_variant_id": item.product_variant_id,
                "product_color_id": item.product_color_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_nominal": item.discount_nominal,
                "discount_percent": item.discount_percent,
                "total": item.total,
                "weight": item.weight,
                "name": item.name,
                "item_notes": item.item_notes,
                "meta": item.meta,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "slug": item.product.slug,
                    "base_price": item.product.base_price,
                } if item.product else None,
                "variant": {
                    "id": item.variant.id,
                    "product_id": item.variant.product_id,
                    "variant_name": item.variant.variant_name,
                    "price": item.variant.price,
                    "sku": item.variant.sku,
                } if item.variant else None,
            }
            for item in (order.items or [])
        ],
    }


class OrderService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(Order.deleted.is_(False))
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(Order).where(Order.deleted.is_(False))

        for key, value in filters.items():
            if hasattr(Order, key):
                query = query.where(getattr(Order, key) == value)
                count_query = count_query.where(getattr(Order, key) == value)

        result = await db.execute(query)
        orders = result.scalars().all()
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        return {
            "data": [_order_to_dict(o) for o in orders],
            "total_count": total,
            "has_more": (skip + len(orders)) < total,
        }

    async def get_by_id(self, db: AsyncSession, order_id: UUID) -> dict[str, Any]:
        query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(Order.id == order_id, Order.deleted.is_(False))
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        if not order:
            raise ResourceNotFoundError(f"Order with ID {order_id} not found")
        return _order_to_dict(order)

    async def create(self, db: AsyncSession, order_in: OrderCreate) -> Any:
        order_data = order_in.model_dump(exclude={"items"})
        
        # Inject platform info into meta
        meta = order_data.get("meta") or {}
        meta["platform"] = "mobile_app"
        order_data["meta"] = meta
        
        order = Order(**order_data)
        db.add(order)
        await db.flush()

        for item_in in order_in.items:
            item_data = item_in.model_dump()
            order_item = OrderItem(order_id=order.id, **item_data)
            db.add(order_item)

        await db.commit()
        return await self.get_by_id(db, order.id)

    async def update(self, db: AsyncSession, order_id: UUID, order_in: OrderUpdate) -> Any:
        order = await crud_orders.get(db=db, id=order_id, deleted=False)
        if not order:
            raise ResourceNotFoundError(f"Order with ID {order_id} not found")

        update_data = order_in.model_dump(exclude_unset=True)
        await crud_orders.update(db=db, db_obj=order, obj_in=update_data)
        await db.commit()
        return await self.get_by_id(db, order_id)

    async def delete(self, db: AsyncSession, order_id: UUID) -> None:
        order = await crud_orders.get(db=db, id=order_id, deleted=False)
        if not order:
            raise ResourceNotFoundError(f"Order with ID {order_id} not found")
        await crud_orders.delete(db=db, id=order_id)
        await db.commit()


order_service = OrderService()
