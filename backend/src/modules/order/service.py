from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from .crud import crud_orders
from .models import Order, OrderItem
from ..add_to_cart.models import AddToCartItem
import datetime
import random
import string
from .schemas import OrderCreate

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
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_nominal": item.discount_nominal,
                "discount_percent": item.discount_percent,
                "total": item.total,
                "name": item.name,
                "item_notes": item.item_notes,
                "meta": item.meta,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "slug": item.product.slug,
                } if item.product else None,
                "variant": {
                    "id": item.variant.id,
                    "product_id": item.variant.product_id,
                    "variant_name": item.variant.variant_name,
                    "sell_price": item.variant.sell_price,
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
        order_data = order_in.model_dump(exclude={"items", "cart_item_ids", "shipping_address_id", "courier_id", "shipping_cost", "voucher_id"})
        
        # Generate Order Number
        now = datetime.datetime.now()
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order_number = f"ORD-{now.strftime('%y%m%d')}-{random_str}"
        order_data["order_number"] = order_number

        # Map mobile fields to db fields
        if order_in.courier_id:
            order_data["courier_id"] = order_in.courier_id
        if order_in.shipping_cost:
            order_data["shipping_cost"] = order_in.shipping_cost
        if order_in.voucher_id:
            order_data["voucher_id"] = order_in.voucher_id
        if order_in.shipping_address_id:
            order_data["shipping_addresses_id"] = order_in.shipping_address_id

        # Inject platform info into meta
        meta = order_data.get("meta") or {}
        meta["platform"] = "mobile_app"
        order_data["meta"] = meta
        
        order = Order(**order_data)
        db.add(order)
        await db.flush()

        # Handle Cart Flow
        if order_in.cart_item_ids:
            for cart_item_id in order_in.cart_item_ids:
                cart_item = await db.scalar(select(AddToCartItem).where(AddToCartItem.id == cart_item_id))
                if cart_item:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=cart_item.product_id,
                        product_variant_id=cart_item.product_variant_id,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.unit_price,
                        discount_nominal=cart_item.discount_nominal,
                        discount_percent=cart_item.discount_percent,
                        total=cart_item.total,
                        name=cart_item.name,
                        item_notes=cart_item.item_notes,
                        meta=cart_item.meta
                    )
                    db.add(order_item)
                    await db.delete(cart_item) # Remove from cart
        # Handle Direct Purchase Flow
        elif order_in.items:
            for item_in in order_in.items:
                item_data = item_in.model_dump(exclude_unset=True)
                order_item = OrderItem(order_id=order.id, **item_data)
                db.add(order_item)

        await db.commit()
        return await self.get_by_id(db, order.id)

