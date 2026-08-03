import uuid
from typing import Annotated

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


# --- Nested Schemas ---
class CourierReadNested(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    type: int | None = None
    is_active: bool
    sort_order: int


class ShippingAddressReadNested(BaseModel):
    id: uuid.UUID
    courier_id: uuid.UUID
    sub_district_id: uuid.UUID
    type: int | None = None
    price: float
    is_active: bool
    sort_order: int


# --- Courier Schemas ---
class CourierBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    type: int | None = None
    is_active: bool = True
    sort_order: int = 0


class Courier(CourierBase, TimestampSchema):
    id: uuid.UUID


class CourierCreate(CourierBase):
    pass


class CourierUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    type: int | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CourierRead(CourierBase, TimestampSchema):
    id: uuid.UUID
    shipping_addresses: list[ShippingAddressReadNested] = []


# --- Shipping Address Schemas ---
class ShippingAddressBase(BaseModel):
    courier_id: uuid.UUID
    sub_district_id: uuid.UUID
    type: int | None = None
    price: float = 0.0
    is_active: bool = True
    sort_order: int = 0


class ShippingAddressCreate(ShippingAddressBase):
    pass


class ShippingAddressUpdate(BaseModel):
    courier_id: uuid.UUID | None = None
    sub_district_id: uuid.UUID | None = None
    type: int | None = None
    price: float | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ShippingAddressRead(ShippingAddressBase, TimestampSchema):
    id: uuid.UUID
    courier: CourierReadNested | None = None
