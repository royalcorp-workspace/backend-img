from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ..common.schemas import TimestampSchema
from ..customer.schemas import CustomerRead
from ..product.schemas import ProductRead, ProductVariantRead


class OrderItemBase(BaseModel):
    product_id: UUID | None = None
    product_variant_id: UUID | None = None
    quantity: int = 1
    unit_price: float = 0.0
    discount_nominal: float = 0.0
    discount_percent: float = 0.0
    total: float = 0.0
    name: str | None = None
    item_notes: str | None = None
    meta: dict[str, Any] | None = None


class OrderItemCreate(OrderItemBase):
    product_id: UUID


class OrderItemRead(OrderItemBase):
    id: UUID | None = None
    order_id: UUID | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    product: ProductRead | None = None
    variant: ProductVariantRead | None = None


class OrderVoidRead(BaseModel):
    id: UUID | None = None
    order_id: UUID | None = None
    customer_id: UUID | None = None
    reason: str | None = None
    status: str | None = "gagal transaksi"
    meta: dict[str, Any] | None = None
    created_at: Any | None = None
    updated_at: Any | None = None


class VoidOrderRead(BaseModel):
    id: UUID
    order_number: str | None = None
    customer_id: UUID | None = None
    order_data: dict[str, Any] | None = None
    order_items_data: list[Any] | dict[str, Any] | None = None
    void_reason: str | None = None
    voided_at: Any | None = None
    created_at: Any | None = None
    updated_at: Any | None = None
    status_label: str = "Gagal Transaksi"
    payment_status_label: str = "Gagal Transaksi"
    total: float | None = 0.0
    items: list[dict[str, Any]] = []


class OrderBase(BaseModel):
    customer_id: UUID
    status: int = 0
    payment_method: str | None = None
    payment_status: int | None = 0
    subtotal: float | None = 0.0
    tax: float | None = 0.0
    discount: float | None = 0.0
    total: float | None = 0.0
    notes: str | None = None
    meta: dict[str, Any] | None = None


class Order(OrderBase, TimestampSchema):
    id: UUID


class OrderCreate(OrderBase):
    items: list[OrderItemCreate] = []
    # If checking out from cart, send cart_item_ids
    cart_item_ids: list[UUID] | None = None
    # Additional shipping/address data for mobile
    shipping_address_id: UUID | None = None
    courier_id: UUID | None = None
    shipping_cost: float | None = 0.0
    voucher_id: UUID | None = None


class OrderRead(BaseModel):
    id: UUID
    order_number: str | None = None
    customer_id: UUID | None = None
    status: int | None = 0
    status_label: str | None = None
    status_text: str | None = None
    payment_method: str | None = None
    payment_status: int | None = 0
    payment_status_label: str | None = None
    payment_status_text: str | None = None
    is_void: bool = False
    void_reason: str | None = None
    voided_at: Any | None = None
    subtotal: float | None = 0.0
    tax: float | None = 0.0
    discount: float | None = 0.0
    total: float | None = 0.0
    shipping_cost: float | None = 0.0
    voucher_nominal: float | None = 0.0
    notes: str | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    customer: CustomerRead | None = None
    items: list[OrderItemRead] = []


class OrderHistoryRead(OrderRead):
    pass

