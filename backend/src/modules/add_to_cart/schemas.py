from typing import Any
from uuid import UUID

from pydantic import BaseModel, model_validator

from ..common.schemas import TimestampSchema
from ..customer.schemas import CustomerRead
from ..product.schemas import ProductRead, ProductVariantRead


class AddToCartItemBase(BaseModel):
    product_id: UUID | None = None
    product_variant_id: UUID | None = None
    variant_id: UUID | None = None
    sku: str | None = None
    name: str | None = None
    quantity: int = 1
    unit_price: float = 0.0
    total: float = 0.0
    discount_nominal: float = 0.0
    discount_percent: float = 0.0
    item_notes: str | None = None
    meta: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_variant_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            v_id = data.get("variant_id") or data.get("product_variant_id")
            if v_id:
                data["variant_id"] = v_id
                data["product_variant_id"] = v_id
        return data


class AddToCartItemCreate(AddToCartItemBase):
    pass


class AddToCartItemRead(AddToCartItemBase, TimestampSchema):
    id: UUID
    add_to_cart_id: UUID
    product: ProductRead | None = None
    variant: ProductVariantRead | None = None


class AddToCartBase(BaseModel):
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


class AddToCart(AddToCartBase, TimestampSchema):
    id: UUID


class AddToCartCreate(AddToCartBase):
    items: list[AddToCartItemCreate] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "abc12345",
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
                "customer_phone": "08123456789",
                "subtotal": 1000000.0,
                "tax": 0.0,
                "discount": 0.0,
                "total": 1000000.0,
                "meta": {"source": "mobile_app"},
                "items": [
                    {
                        "product_id": "223e4567-e89b-12d3-a456-426614174000",
                        "product_variant_id": "323e4567-e89b-12d3-a456-426614174000",
                        "name": "KB GRAND X LB-17",
                        "quantity": 1,
                        "unit_price": 1000000.0,
                        "total": 1000000.0,
                        "discount_nominal": 0.0,
                        "discount_percent": 0.0,
                        "item_notes": "Tolong packing aman",
                        "meta": {}
                    }
                ]
            }
        }
    }


class AddToCartUpdate(BaseModel):
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


class AddToCartRead(AddToCartBase, TimestampSchema):
    id: UUID
    customer: CustomerRead | None = None
    items: list[AddToCartItemRead] = []


class AddToCartCheckout(BaseModel):
    payment_method: str | None = None
    payment_status: int | None = None
    notes: str | None = None
    meta: dict[str, Any] | None = None
