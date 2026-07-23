from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ..common.schemas import TimestampSchema
from ..customer.schemas import CustomerRead
from ..product.schemas import ProductRead, ProductVariantRead


class BufferItemBase(BaseModel):
    product_id: UUID
    product_variant_id: UUID | None = None
    name: str | None = None
    quantity: int = 1
    unit_price: float = 0.0
    total: float = 0.0
    discount_nominal: float = 0.0
    discount_percent: float = 0.0
    item_notes: str | None = None
    meta: dict[str, Any] | None = None


class BufferItemCreate(BufferItemBase):
    pass


class BufferItemRead(BufferItemBase, TimestampSchema):
    id: UUID
    buffer_id: UUID
    product: ProductRead | None = None
    variant: ProductVariantRead | None = None


class BufferBase(BaseModel):
    customer_id: UUID | None = None
    session_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    subtotal: float | None = 0.0
    tax: float | None = 0.0
    discount: float | None = 0.0
    total: float | None = 0.0
    meta: dict[str, Any] | None = None


class Buffer(BufferBase, TimestampSchema):
    id: UUID


class BufferCreate(BufferBase):
    pass


class BufferUpdate(BaseModel):
    customer_id: UUID | None = None
    session_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    discount: float | None = None
    total: float | None = None
    meta: dict[str, Any] | None = None


class BufferRead(BufferBase, TimestampSchema):
    id: UUID
    customer: CustomerRead | None = None
    items: list[BufferItemRead] = []


class BufferCheckout(BaseModel):
    payment_method: str | None = None
    payment_status: int | None = None
    notes: str | None = None
    meta: dict[str, Any] | None = None
