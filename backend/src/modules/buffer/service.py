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
from .crud import crud_buffer_items, crud_buffers
from .models import Buffer, BufferItem
from .schemas import BufferCheckout, BufferCreate, BufferItemCreate, BufferUpdate

logger = get_logger()


def _buffer_to_dict(buffer: Buffer) -> dict[str, Any]:
    return {
        "id": buffer.id,
        "customer_id": buffer.customer_id,
        "session_id": buffer.session_id,
        "customer_name": buffer.customer_name,
        "customer_email": buffer.customer_email,
        "customer_phone": buffer.customer_phone,
        "subtotal": buffer.subtotal,
        "tax": buffer.tax,
        "discount": buffer.discount,
        "total": buffer.total,
        "meta": buffer.meta,
        "creator": buffer.creator,
        "editor": buffer.editor,
        "created_at": buffer.created_at,
        "updated_at": buffer.updated_at,
        "customer": {
            "id": buffer.customer.id,
            "name": buffer.customer.name,
            "email": buffer.customer.email,
            "phone": buffer.customer.phone,
            "user_id": buffer.customer.user_id,
            "created_at": buffer.customer.created_at,
            "updated_at": buffer.customer.updated_at,
            "deleted": buffer.customer.deleted,
        } if buffer.customer else None,
        "items": [
            {
                "id": item.id,
                "buffer_id": item.buffer_id,
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
            for item in (buffer.items or [])
        ],
    }


def _recalculate_buffer_totals(buffer: Buffer) -> None:
    subtotal = sum((item.unit_price or 0.0) * (item.quantity or 0) for item in (buffer.items or []))
    discount = sum(
        (item.discount_nominal or 0.0)
        + ((item.unit_price or 0.0) * (item.quantity or 0) * (item.discount_percent or 0.0) / 100)
        for item in (buffer.items or [])
    )
    buffer.subtotal = subtotal
    buffer.discount = discount
    buffer.tax = 0.0
    buffer.total = subtotal - discount + buffer.tax


class BufferService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters) -> dict[str, Any]:
        query = (
            select(Buffer)
            .options(
                selectinload(Buffer.customer),
                selectinload(Buffer.items).selectinload(BufferItem.product),
                selectinload(Buffer.items).selectinload(BufferItem.variant),
            )
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(Buffer)

        for key, value in filters.items():
            if hasattr(Buffer, key):
                query = query.where(getattr(Buffer, key) == value)
                count_query = count_query.where(getattr(Buffer, key) == value)

        result = await db.execute(query)
        buffers = result.scalars().all()
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        return {
            "data": [_buffer_to_dict(b) for b in buffers],
            "total_count": total,
            "has_more": (skip + len(buffers)) < total,
        }

    async def get_by_id(self, db: AsyncSession, buffer_id: UUID) -> dict[str, Any]:
        query = (
            select(Buffer)
            .options(
                selectinload(Buffer.customer),
                selectinload(Buffer.items).selectinload(BufferItem.product),
                selectinload(Buffer.items).selectinload(BufferItem.variant),
            )
            .where(Buffer.id == buffer_id)
        )
        result = await db.execute(query)
        buffer = result.scalar_one_or_none()
        if not buffer:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} not found")
        return _buffer_to_dict(buffer)

    async def create(self, db: AsyncSession, buffer_in: BufferCreate) -> dict[str, Any]:
        buffer_data = buffer_in.model_dump()
        buffer = Buffer(**buffer_data)
        db.add(buffer)
        await db.commit()
        return await self.get_by_id(db, buffer.id)

    async def update(self, db: AsyncSession, buffer_id: UUID, buffer_in: BufferUpdate) -> dict[str, Any]:
        buffer = await crud_buffers.get(db=db, id=buffer_id)
        if not buffer:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} not found")

        update_data = buffer_in.model_dump(exclude_unset=True)
        await crud_buffers.update(db=db, db_obj=buffer, obj_in=update_data)
        await db.commit()
        return await self.get_by_id(db, buffer_id)

    async def delete(self, db: AsyncSession, buffer_id: UUID) -> None:
        buffer = await crud_buffers.get(db=db, id=buffer_id)
        if not buffer:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} not found")
        await db.delete(buffer)
        await db.commit()

    async def add_item(self, db: AsyncSession, buffer_id: UUID, item_in: BufferItemCreate) -> dict[str, Any]:
        buffer = await crud_buffers.get(db=db, id=buffer_id)
        if not buffer:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} not found")

        item_data = item_in.model_dump()
        item_data["buffer_id"] = buffer_id
        item = BufferItem(**item_data)
        db.add(item)
        await db.flush()

        await db.refresh(buffer)
        _recalculate_buffer_totals(buffer)
        await db.commit()
        await db.refresh(buffer)

        query = (
            select(BufferItem)
            .options(selectinload(BufferItem.product), selectinload(BufferItem.variant))
            .where(BufferItem.id == item.id)
        )
        result = await db.execute(query)
        new_item = result.scalar_one()

        return {
            "id": new_item.id,
            "buffer_id": new_item.buffer_id,
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
                "base_price": new_item.product.base_price,
            } if new_item.product else None,
            "variant": {
                "id": new_item.variant.id,
                "product_id": new_item.variant.product_id,
                "variant_name": new_item.variant.variant_name,
                "price": new_item.variant.price,
                "sku": new_item.variant.sku,
            } if new_item.variant else None,
        }

    async def update_item(self, db: AsyncSession, buffer_id: UUID, item_id: UUID, item_in: BufferItemCreate) -> dict[str, Any]:
        buffer = await crud_buffers.get(db=db, id=buffer_id)
        if not buffer:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} not found")

        item = await crud_buffer_items.get(db=db, id=item_id)
        if not item or item.buffer_id != buffer_id:
            raise ResourceNotFoundError(f"Buffer item with ID {item_id} not found in buffer {buffer_id}")

        update_data = item_in.model_dump(exclude_unset=True)
        await crud_buffer_items.update(db=db, db_obj=item, obj_in=update_data)
        await db.flush()

        await db.refresh(buffer)
        _recalculate_buffer_totals(buffer)
        await db.commit()
        await db.refresh(buffer)

        query = (
            select(BufferItem)
            .options(selectinload(BufferItem.product), selectinload(BufferItem.variant))
            .where(BufferItem.id == item_id)
        )
        result = await db.execute(query)
        updated_item = result.scalar_one()

        return {
            "id": updated_item.id,
            "buffer_id": updated_item.buffer_id,
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
                "base_price": updated_item.product.base_price,
            } if updated_item.product else None,
            "variant": {
                "id": updated_item.variant.id,
                "product_id": updated_item.variant.product_id,
                "variant_name": updated_item.variant.variant_name,
                "price": updated_item.variant.price,
                "sku": updated_item.variant.sku,
            } if updated_item.variant else None,
        }

    async def delete_item(self, db: AsyncSession, buffer_id: UUID, item_id: UUID) -> None:
        buffer = await crud_buffers.get(db=db, id=buffer_id)
        if not buffer:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} not found")

        item = await crud_buffer_items.get(db=db, id=item_id)
        if not item or item.buffer_id != buffer_id:
            raise ResourceNotFoundError(f"Buffer item with ID {item_id} not found in buffer {buffer_id}")

        await db.delete(item)
        await db.flush()

        await db.refresh(buffer)
        _recalculate_buffer_totals(buffer)
        await db.commit()

    async def checkout(self, db: AsyncSession, buffer_id: UUID, checkout_in: BufferCheckout, creator_id: UUID | None = None) -> dict[str, Any]:
        buffer = await crud_buffers.get(db=db, id=buffer_id)
        if not buffer:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} not found")

        items = buffer.items or []
        if not items:
            raise ResourceNotFoundError(f"Buffer with ID {buffer_id} is empty")

        customer = await db.get(Customer, buffer.customer_id) if buffer.customer_id else None
        if not customer:
            customer = Customer(
                name=buffer.customer_name or "Guest",
                email=buffer.customer_email,
                phone=buffer.customer_phone,
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
            subtotal=buffer.subtotal or 0.0,
            tax=buffer.tax or 0.0,
            discount=buffer.discount or 0.0,
            total=buffer.total or 0.0,
            notes=checkout_in.notes,
            meta=checkout_in.meta or buffer.meta,
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

        await db.delete(buffer)
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
                for item in (new_order.items or [])
            ],
        }


buffer_service = BufferService()
