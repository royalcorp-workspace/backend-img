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
from .models import AddToCart, AddToCartItem
from .schemas import AddToCartCheckout, AddToCartCreate, AddToCartItemCreate, AddToCartUpdate

logger = get_logger()


def _item_to_dict(item: AddToCartItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "add_to_cart_id": item.add_to_cart_id,
        "product_id": item.product_id,
        "product_variant_id": item.product_variant_id,
        "variant_id": item.product_variant_id,
        "sku": item.variant.sku if item.variant else None,
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
            _item_to_dict(item)
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


def _calculate_item_total(
    unit_price: float | None,
    quantity: int | None,
    discount_nominal: float | None,
    discount_percent: float | None,
) -> float:
    qty = quantity if quantity and quantity > 0 else 1
    price = unit_price or 0.0
    subtotal = price * qty
    disc = (discount_nominal or 0.0) + (subtotal * (discount_percent or 0.0) / 100.0)
    return max(0.0, subtotal - disc)


async def _resolve_item_info(
    db: AsyncSession, item_in: AddToCartItemCreate
) -> tuple[UUID, UUID | None, ProductVariant | None]:
    target_product_id = item_in.product_id
    target_variant_id = item_in.product_variant_id or getattr(item_in, "variant_id", None)
    variant: ProductVariant | None = None

    if target_variant_id:
        v_res = await db.execute(select(ProductVariant).where(ProductVariant.id == target_variant_id))
        variant = v_res.scalar_one_or_none()
        if variant:
            if not target_product_id:
                target_product_id = variant.product_id
        else:
            raise ResourceNotFoundError(f"ProductVariant with ID {target_variant_id} not found")
    elif item_in.sku:
        v_res = await db.execute(select(ProductVariant).where(ProductVariant.sku == item_in.sku))
        variant = v_res.scalar_one_or_none()
        if variant:
            target_variant_id = variant.id
            if not target_product_id:
                target_product_id = variant.product_id
        else:
            raise ResourceNotFoundError(f"ProductVariant with SKU '{item_in.sku}' not found")

    if not target_product_id:
        raise ResourceNotFoundError("Either product_id, product_variant_id, variant_id, or sku must be provided")

    return target_product_id, target_variant_id, variant


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
        
        # Add items if provided (grouping items with the same SKU / variant)
        added_items: dict[tuple[UUID, UUID | None], AddToCartItem] = {}
        for item_in in buffer_in.items:
            target_product_id, target_variant_id, variant = await _resolve_item_info(db, item_in)
            key = (target_product_id, target_variant_id)
            qty_to_add = item_in.quantity if item_in.quantity and item_in.quantity > 0 else 1

            if key in added_items:
                existing = added_items[key]
                existing.quantity += qty_to_add
                if item_in.unit_price and item_in.unit_price > 0:
                    existing.unit_price = item_in.unit_price
                if item_in.item_notes:
                    existing.item_notes = item_in.item_notes
                existing.total = _calculate_item_total(
                    existing.unit_price,
                    existing.quantity,
                    existing.discount_nominal,
                    existing.discount_percent,
                )
            else:
                item_data = item_in.model_dump(exclude={"sku", "variant_id"} if hasattr(item_in, "sku") else set())
                item_data.pop("sku", None)
                item_data.pop("variant_id", None)
                item_data["add_to_cart_id"] = add_to_cart.id
                item_data["product_id"] = target_product_id
                item_data["product_variant_id"] = target_variant_id
                item_data["quantity"] = qty_to_add

                if not item_data.get("unit_price") and variant and variant.sell_price:
                    item_data["unit_price"] = variant.sell_price

                if not item_data.get("name") and variant and variant.variant_name:
                    item_data["name"] = variant.variant_name

                item_data["total"] = _calculate_item_total(
                    item_data.get("unit_price"),
                    item_data.get("quantity"),
                    item_data.get("discount_nominal"),
                    item_data.get("discount_percent"),
                )

                cart_item = AddToCartItem(**item_data)
                db.add(cart_item)
                added_items[key] = cart_item
            
        await db.flush()
        await db.refresh(add_to_cart, ["items"])
        _recalculate_add_to_cart_totals(add_to_cart)
        await db.commit()
        return await self.get_by_id(db, add_to_cart.id)

    async def update(self, db: AsyncSession, add_to_cart_id: UUID, buffer_in: AddToCartUpdate) -> dict[str, Any]:
        query = select(AddToCart).where(AddToCart.id == add_to_cart_id)
        result = await db.execute(query)
        add_to_cart = result.scalar_one_or_none()
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        update_data = buffer_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(add_to_cart, key, value)
        await db.commit()
        return await self.get_by_id(db, add_to_cart_id)

    async def delete(self, db: AsyncSession, add_to_cart_id: UUID) -> None:
        query = select(AddToCart).where(AddToCart.id == add_to_cart_id)
        result = await db.execute(query)
        add_to_cart = result.scalar_one_or_none()
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")
        await db.delete(add_to_cart)
        await db.commit()

    async def add_item(self, db: AsyncSession, add_to_cart_id: UUID, item_in: AddToCartItemCreate) -> dict[str, Any]:
        query = (
            select(AddToCart)
            .options(
                selectinload(AddToCart.items).selectinload(AddToCartItem.product),
                selectinload(AddToCart.items).selectinload(AddToCartItem.variant),
            )
            .where(AddToCart.id == add_to_cart_id)
        )
        result = await db.execute(query)
        add_to_cart = result.scalar_one_or_none()
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        target_product_id, target_variant_id, variant = await _resolve_item_info(db, item_in)

        # Check if an item with the same variant_id (or same product without variant) already exists
        existing_item: AddToCartItem | None = None
        for cart_item in (add_to_cart.items or []):
            if target_variant_id is not None:
                if cart_item.product_variant_id == target_variant_id or (
                    cart_item.product_variant_id and str(cart_item.product_variant_id) == str(target_variant_id)
                ):
                    existing_item = cart_item
                    break
            else:
                if (
                    cart_item.product_variant_id is None
                    and (cart_item.product_id == target_product_id or str(cart_item.product_id) == str(target_product_id))
                ):
                    existing_item = cart_item
                    break

        qty_to_add = item_in.quantity if item_in.quantity and item_in.quantity > 0 else 1

        if existing_item:
            existing_item.quantity += qty_to_add
            if item_in.unit_price and item_in.unit_price > 0:
                existing_item.unit_price = item_in.unit_price
            if item_in.item_notes:
                existing_item.item_notes = item_in.item_notes
            if item_in.discount_nominal is not None and item_in.discount_nominal > 0:
                existing_item.discount_nominal = item_in.discount_nominal
            if item_in.discount_percent is not None and item_in.discount_percent > 0:
                existing_item.discount_percent = item_in.discount_percent

            existing_item.total = _calculate_item_total(
                existing_item.unit_price,
                existing_item.quantity,
                existing_item.discount_nominal,
                existing_item.discount_percent,
            )

            await db.flush()
            _recalculate_add_to_cart_totals(add_to_cart)
            await db.commit()

            query_item = (
                select(AddToCartItem)
                .options(selectinload(AddToCartItem.product), selectinload(AddToCartItem.variant))
                .where(AddToCartItem.id == existing_item.id)
            )
            result_item = await db.execute(query_item)
            return _item_to_dict(result_item.scalar_one())

        item_data = item_in.model_dump(exclude={"sku", "variant_id"} if hasattr(item_in, "sku") else set())
        item_data.pop("sku", None)
        item_data.pop("variant_id", None)
        item_data["add_to_cart_id"] = add_to_cart_id
        item_data["product_id"] = target_product_id
        item_data["product_variant_id"] = target_variant_id
        item_data["quantity"] = qty_to_add

        if not item_data.get("unit_price") and variant and variant.sell_price:
            item_data["unit_price"] = variant.sell_price

        if not item_data.get("name") and variant and variant.variant_name:
            item_data["name"] = variant.variant_name

        item_data["total"] = _calculate_item_total(
            item_data.get("unit_price"),
            item_data.get("quantity"),
            item_data.get("discount_nominal"),
            item_data.get("discount_percent"),
        )

        item = AddToCartItem(**item_data)
        db.add(item)
        await db.flush()

        await db.refresh(add_to_cart, ["items"])
        _recalculate_add_to_cart_totals(add_to_cart)
        await db.commit()

        query_item = (
            select(AddToCartItem)
            .options(selectinload(AddToCartItem.product), selectinload(AddToCartItem.variant))
            .where(AddToCartItem.id == item.id)
        )
        result_item = await db.execute(query_item)
        new_item = result_item.scalar_one()

        return _item_to_dict(new_item)

    async def update_item(self, db: AsyncSession, add_to_cart_id: UUID, item_id: UUID, item_in: AddToCartItemCreate) -> dict[str, Any]:
        query = (
            select(AddToCart)
            .options(selectinload(AddToCart.items))
            .where(AddToCart.id == add_to_cart_id)
        )
        result = await db.execute(query)
        add_to_cart = result.scalar_one_or_none()
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        query_item = select(AddToCartItem).where(AddToCartItem.id == item_id)
        result_item = await db.execute(query_item)
        item = result_item.scalar_one_or_none()
        if not item or item.add_to_cart_id != add_to_cart_id:
            raise ResourceNotFoundError(f"AddToCart item with ID {item_id} not found in add_to_cart {add_to_cart_id}")

        update_data = item_in.model_dump(exclude_unset=True, exclude={"sku", "variant_id"} if hasattr(item_in, "sku") else set())
        update_data.pop("sku", None)
        update_data.pop("variant_id", None)
        for key, value in update_data.items():
            setattr(item, key, value)

        item.total = _calculate_item_total(
            item.unit_price,
            item.quantity,
            item.discount_nominal,
            item.discount_percent,
        )
        await db.flush()

        await db.refresh(add_to_cart, ["items"])
        _recalculate_add_to_cart_totals(add_to_cart)
        await db.commit()

        query_updated = (
            select(AddToCartItem)
            .options(selectinload(AddToCartItem.product), selectinload(AddToCartItem.variant))
            .where(AddToCartItem.id == item_id)
        )
        result_updated = await db.execute(query_updated)
        updated_item = result_updated.scalar_one()

        return _item_to_dict(updated_item)

    async def delete_item(self, db: AsyncSession, add_to_cart_id: UUID, item_id: UUID) -> None:
        query = (
            select(AddToCart)
            .options(selectinload(AddToCart.items))
            .where(AddToCart.id == add_to_cart_id)
        )
        result = await db.execute(query)
        add_to_cart = result.scalar_one_or_none()
        if not add_to_cart:
            raise ResourceNotFoundError(f"AddToCart with ID {add_to_cart_id} not found")

        query_item = select(AddToCartItem).where(AddToCartItem.id == item_id)
        result_item = await db.execute(query_item)
        item = result_item.scalar_one_or_none()
        if not item or item.add_to_cart_id != add_to_cart_id:
            raise ResourceNotFoundError(f"AddToCart item with ID {item_id} not found in add_to_cart {add_to_cart_id}")

        await db.delete(item)
        await db.flush()

        await db.refresh(add_to_cart, ["items"])
        if not add_to_cart.items or len(add_to_cart.items) == 0:
            await db.delete(add_to_cart)
            await db.commit()
            return

        _recalculate_add_to_cart_totals(add_to_cart)
        await db.commit()

    async def checkout(self, db: AsyncSession, add_to_cart_id: UUID, checkout_in: AddToCartCheckout, creator_id: UUID | None = None) -> dict[str, Any]:
        query = (
            select(AddToCart)
            .options(
                selectinload(AddToCart.customer),
                selectinload(AddToCart.items).selectinload(AddToCartItem.product),
            )
            .where(AddToCart.id == add_to_cart_id)
        )
        result = await db.execute(query)
        add_to_cart = result.scalar_one_or_none()
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
                name=item.name or (item.product.name if item.product else "Product"),
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

        query_order = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(Order.id == order.id)
        )
        result_order = await db.execute(query_order)
        new_order = result_order.scalar_one()

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
                for item in (new_order.items or [])
            ],
        }


add_to_cart_service = AddToCartService()
