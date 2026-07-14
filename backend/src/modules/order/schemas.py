from pydantic import BaseModel

from ..common.schemas import TimestampSchema
from ..customer.schemas import CustomerRead
from ..product.schemas import ProductRead, ProductVariantRead


class OrderItemBase(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = 1
    price: float = 0.0
    discount: float = 0.0
    total: float = 0.0


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemRead(OrderItemBase, TimestampSchema):
    id: int
    order_id: int
    product: ProductRead | None = None
    variant: ProductVariantRead | None = None


class OrderBase(BaseModel):
    customer_id: int
    status: int = 0
    payment_method: str | None = None
    payment_status: str | None = None
    subtotal: float | None = 0.0
    tax: float | None = 0.0
    discount: float | None = 0.0
    total: float | None = 0.0
    notes: str | None = None
    meta: str | None = None


class Order(OrderBase, TimestampSchema):
    id: int


class OrderCreate(OrderBase):
    items: list[OrderItemCreate] = []


class OrderUpdate(BaseModel):
    customer_id: int | None = None
    status: int | None = None
    payment_method: str | None = None
    payment_status: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    discount: float | None = None
    total: float | None = None
    notes: str | None = None
    meta: str | None = None


class OrderRead(OrderBase, TimestampSchema):
    id: int
    customer: CustomerRead | None = None
    items: list[OrderItemRead] = []
