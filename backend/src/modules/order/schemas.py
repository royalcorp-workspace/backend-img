from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ..common.schemas import TimestampSchema
from ..customer.schemas import CustomerRead
from ..product.schemas import ProductRead, ProductVariantRead


class OrderItemBase(BaseModel):
    product_id: UUID
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
    pass


class OrderItemRead(OrderItemBase, TimestampSchema):
    id: UUID
    order_id: UUID
    product: ProductRead | None = None
    variant: ProductVariantRead | None = None


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


    total: float | None = None
    notes: str | None = None
    meta: dict[str, Any] | None = None


class OrderRead(OrderBase, TimestampSchema):
    id: UUID
    customer: CustomerRead | None = None
    items: list[OrderItemRead] = []
