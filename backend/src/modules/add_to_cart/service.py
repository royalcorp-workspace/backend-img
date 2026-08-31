from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceNotFoundError
from ..customer.models import Customer
from ..order.models import Order, OrderItem
from ..product.models import Product, ProductVariant
from .crud import crud_add_to_cart_items, crud_add_to_carts
from .models import AddToCart, AddToCartItem, AddToCartItem
from .schemas import AddToCartCheckout, AddToCartCreate, AddToCartItemCreate, AddToCartUpdate

logger = get_logger()


def _add_to_cart_to_dict(add_to_cart: AddToCart) -> dict[str, Any]:
    return {
        "id": add_to_cart.id,
        "customer_id": add_to_cart.customer_id,
        "session_id": add_to_cart.session_id,
        "customer_name": add_to_cart.customer_name,
        "customer_email": add_to_cart.customer_email,
        "customer_phone": add_to_cart.customer_phone,
        "subtotal": add_to_cart.subtotal,
        "tax": add_to_cart.tax,
        "discount": add_to_cart.discount,
        "total": add_to_cart.total,
        "meta": add_to_cart.meta,
        "creator": add_to_cart.creator,
        "editor": add_to_cart.editor,
        "created_at": add_to_cart.created_at,
        "updated_at": add_to_cart.updated_at,
        "customer": {
            "id": add_to_cart.customer.id,
            "name": add_to_cart.customer.name,
            "email": add_to_cart.customer.email,
            "phone": add_to_cart.customer.phone,
            "user_id": add_to_cart.customer.user_id,
            "created_at": add_to_cart.customer.created_at,
            "updated_at": add_to_cart.customer.updated_at,
            "deleted": add_to_cart.customer.deleted,
        } if add_to_cart.customer else None,
        "items": [
            {
                "id": item.id,
                "add_to_cart_id": item.add_to_cart_id,
                "product_id": item.product_id,
                "product_variant_id": item.product_variant_id,
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total": item.total,
                "discount_nominal": item.discount_nominal,
                "discount_percent": item.discount_percent,
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
            for item in (add_to_cart.items or [])
        ],
    }


def _recalculate_add_to_cart_totals(add_to_cart: AddToCart) -> None:
    subtotal = sum((item.unit_price or 0.0) * (item.quantity or 0) for item in (add_to_cart.items or []))
    discount = sum(
        (item.discount_nominal or 0.0)
        + ((item.unit_price or 0.0) * (item.quantity or 0) * (item.discount_percent or 0.0) / 100)
        for item in (add_to_cart.items or [])
    )
    add_to_cart.subtotal = subtotal
    add_to_cart.discount = discount
    add_to_cart.tax = 0.0
    add_to_cart.total = subtotal - discount + add_to_cart.tax


class AddToCartService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters) -> dict[str, Any]:
        query = (
            select(AddToCart)
            .options(
                selectinload(AddToCart.customer),
                selectinload(AddToCart.items).selectinload(AddToCartItem.product),
                selectinload(AddToCart.items).selectinload(AddToCartItem.variant),
            )
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(AddToCart)

        for key, value in filters.items():
            if hasattr(AddToCart, key):
                query = query.where(getattr(AddToCart, key) == value)
                count_query = count_query.where(getattr(AddToCart, key) == value)

        result = await db.execute(query)
        buffers = result.scalars().all()
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        return {
            "data": [_add_to_cart_to_dict(b) for b in buffers],
            "total_count": total,
            "has_more": (skip + len(buffers)) < total,
        }

    async def get_by_id(self, db: AsyncSession, add_to_cart_id: UUID) -> dict[str, Any]:
        query = (
            select(AddToCart)
            .options(
                selectinload(AddToCart.customer),
                selectinload(AddToCart.items).selectinload(AddToCartItem.product),
                selectinload(AddToCart.items).selectinload(AddToCartItem.variant),
            )
            .where(AddToCart.id == add_to_cart_id)
        )
        result = await db.execute(query)
        add_to_cart = result.scalar_one_or_none()
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")
        return _add_to_cart_to_dict(add_to_cart)

    async def create(self, db: AsyncSession, buffer_in: AddToCartCreate) -> dict[str, Any]:
        buffer_data = buffer_in.model_dump(exclude={"items"})
        add_to_cart = AddToCart(**buffer_data)
        db.add(add_to_cart)
        await db.flush()
        
        # Add items if provided
        for item_in in buffer_in.items:
            item_data = item_in.model_dump()
            cart_item = AddToCartItem(add_to_cart_id=add_to_cart.id, **item_data)
            logger.warning(f'DEBUG ITEM DATA: {item_data} | CART ITEM: {cart_item.product_variant_id}')
            db.add(cart_item)
            
        await db.flush()
        
        # We need to refresh the relationships to calculate totals
        await db.refresh(add_to_cart, ["items"])
        
        # Recalculate totals
        _recalculate_add_to_cart_totals(add_to_cart)
        
        await db.commit()
        return await self.get_by_id(db, add_to_cart.id)

    async def update(self, db: AsyncSession, add_to_cart_id: UUID, buffer_in: AddToCartUpdate) -> dict[str, Any]:
        add_to_cart = await crud_add_to_carts.get(db=db, id=add_to_cart_id)
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        update_data = buffer_in.model_dump(exclude_unset=True)
        await crud_add_to_carts.update(db=db, db_obj=add_to_cart, obj_in=update_data)
        await db.commit()
        return await self.get_by_id(db, add_to_cart_id)

    async def delete(self, db: AsyncSession, add_to_cart_id: UUID) -> None:
        add_to_cart = await crud_add_to_carts.get(db=db, id=add_to_cart_id)
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")
        await db.delete(add_to_cart)
        await db.commit()

    async def add_item(self, db: AsyncSession, add_to_cart_id: UUID, item_in: AddToCartItemCreate) -> dict[str, Any]:
        add_to_cart = await crud_add_to_carts.get(db=db, id=add_to_cart_id)
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        item_data = item_in.model_dump()
        item_data["add_to_cart_id"] = add_to_cart_id
        item = AddToCartItem(**item_data)
        db.add(item)
        await db.flush()

        await db.refresh(add_to_cart)
        _recalculate_add_to_cart_totals(add_to_cart)
        await db.commit()
        await db.refresh(add_to_cart)

        query = (
            select(AddToCartItem)
            .options(selectinload(AddToCartItem.product), selectinload(AddToCartItem.variant))
            .where(AddToCartItem.id == item.id)
        )
        result = await db.execute(query)
        new_item = result.scalar_one()

        return {
            "id": new_item.id,
            "add_to_cart_id": new_item.add_to_cart_id,
            "product_id": new_item.product_id,
            "product_variant_id": new_item.product_variant_id,
            "name": new_item.name,
            "quantity": new_item.quantity,
            "unit_price": new_item.unit_price,
            "total": new_item.total,
            "discount_nominal": new_item.discount_nominal,
            "discount_percent": new_item.discount_percent,
            "item_notes": new_item.item_notes,
            "meta": new_item.meta,
            "created_at": new_item.created_at,
            "updated_at": new_item.updated_at,
            "product": {
                "id": new_item.product.id,
                "name": new_item.product.name,
                "slug": new_item.product.slug,
            } if new_item.product else None,
            "variant": {
                "id": new_item.variant.id,
                "product_id": new_item.variant.product_id,
                "variant_name": new_item.variant.variant_name,
                "sell_price": new_item.variant.sell_price,
                "sku": new_item.variant.sku,
            } if new_item.variant else None,
        }

    async def update_item(self, db: AsyncSession, add_to_cart_id: UUID, item_id: UUID, item_in: AddToCartItemCreate) -> dict[str, Any]:
        add_to_cart = await crud_add_to_carts.get(db=db, id=add_to_cart_id)
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        item = await crud_add_to_cart_items.get(db=db, id=item_id)
        if not item or item.add_to_cart_id != add_to_cart_id:
            raise ResourceNotFoundError(f"AddToCart item with ID {item_id} not found in add_to_cart {add_to_cart_id}")

        update_data = item_in.model_dump(exclude_unset=True)
        await crud_add_to_cart_items.update(db=db, db_obj=item, obj_in=update_data)
        await db.flush()

        await db.refresh(add_to_cart)
        _recalculate_add_to_cart_totals(add_to_cart)
        await db.commit()
        await db.refresh(add_to_cart)

        query = (
            select(AddToCartItem)
            .options(selectinload(AddToCartItem.product), selectinload(AddToCartItem.variant))
            .where(AddToCartItem.id == item_id)
        )
        result = await db.execute(query)
        updated_item = result.scalar_one()

        return {
            "id": updated_item.id,
            "add_to_cart_id": updated_item.add_to_cart_id,
            "product_id": updated_item.product_id,
            "product_variant_id": updated_item.product_variant_id,
            "name": updated_item.name,
            "quantity": updated_item.quantity,
            "unit_price": updated_item.unit_price,
            "total": updated_item.total,
            "discount_nominal": updated_item.discount_nominal,
            "discount_percent": updated_item.discount_percent,
            "item_notes": updated_item.item_notes,
            "meta": updated_item.meta,
            "created_at": updated_item.created_at,
            "updated_at": updated_item.updated_at,
            "product": {
                "id": updated_item.product.id,
                "name": updated_item.product.name,
                "slug": updated_item.product.slug,
            } if updated_item.product else None,
            "variant": {
                "id": updated_item.variant.id,
                "product_id": updated_item.variant.product_id,
                "variant_name": updated_item.variant.variant_name,
                "sell_price": updated_item.variant.sell_price,
                "sku": updated_item.variant.sku,
            } if updated_item.variant else None,
        }

    async def delete_item(self, db: AsyncSession, add_to_cart_id: UUID, item_id: UUID) -> None:
        add_to_cart = await crud_add_to_carts.get(db=db, id=add_to_cart_id)
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        item = await crud_add_to_cart_items.get(db=db, id=item_id)
        if not item or item.add_to_cart_id != add_to_cart_id:
            raise ResourceNotFoundError(f"AddToCart item with ID {item_id} not found in add_to_cart {add_to_cart_id}")

        await db.delete(item)
        await db.flush()

        await db.refresh(add_to_cart)
        _recalculate_add_to_cart_totals(add_to_cart)
        await db.commit()

    async def checkout(self, db: AsyncSession, add_to_cart_id: UUID, checkout_in: AddToCartCheckout, creator_id: UUID | None = None) -> dict[str, Any]:
        add_to_cart = await crud_add_to_carts.get(db=db, id=add_to_cart_id)
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        items = add_to_cart.items or []
        if not items:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} is empty")

        customer = await db.get(Customer, add_to_cart.customer_id) if add_to_cart.customer_id else None
        if not customer:
            customer = Customer(
                name=add_to_cart.customer_name or "Guest",
                email=add_to_cart.customer_email,
                phone=add_to_cart.customer_phone,
                creator=creator_id,
                editor=creator_id,
            )
            db.add(customer)
            await db.flush()

        order = Order(
            customer_id=customer.id,
            status=Order.STATUS_DRAFT,
            payment_method=checkout_in.payment_method,
            payment_status=checkout_in.payment_status or Order.PAYMENT_UNPAID,
            subtotal=add_to_cart.subtotal or 0.0,
            tax=add_to_cart.tax or 0.0,
            discount=add_to_cart.discount or 0.0,
            total=add_to_cart.total or 0.0,
            notes=checkout_in.notes,
            meta=checkout_in.meta or add_to_cart.meta,
            creator=creator_id,
            editor=creator_id,
        )
        db.add(order)
        await db.flush()

        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_variant_id=item.product_variant_id,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total=item.total,
                discount_nominal=item.discount_nominal,
                discount_percent=item.discount_percent,
                item_notes=item.item_notes,
                meta=item.meta,
            )
            db.add(order_item)

        await db.delete(add_to_cart)
        await db.commit()

        query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(Order.id == order.id)
        )
        result = await db.execute(query)
        new_order = result.scalar_one()

        return {
            "id": new_order.id,
            "customer_id": new_order.customer_id,
            "status": new_order.status,
            "payment_method": new_order.payment_method,
            "payment_status": new_order.payment_status,
            "subtotal": new_order.subtotal,
            "tax": new_order.tax,
            "discount": new_order.discount,
            "total": new_order.total,
            "notes": new_order.notes,
            "meta": new_order.meta,
            "creator": new_order.creator,
            "editor": new_order.editor,
            "deleted": new_order.deleted,
            "created_at": new_order.created_at,
            "updated_at": new_order.updated_at,
            "customer": {
                "id": new_order.customer.id,
                "name": new_order.customer.name,
                "email": new_order.customer.email,
                "phone": new_order.customer.phone,
                "user_id": new_order.customer.user_id,
                "created_at": new_order.customer.created_at,
                "updated_at": new_order.customer.updated_at,
                "deleted": new_order.customer.deleted,
            } if new_order.customer else None,
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
                    } if item.product else None,
                    "variant": {
                        "id": item.variant.id,
                        "product_id": item.variant.product_id,
                        "variant_name": item.variant.variant_name,
                        "sell_price": item.variant.sell_price,
                        "sku": item.variant.sku,
                    } if item.variant else None,
                }
                for item in (new_order.items or [])
            ],
        }


add_to_cart_service = AddToCartService()
