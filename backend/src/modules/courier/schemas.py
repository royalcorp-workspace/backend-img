from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


# --- Nested Schemas ---
class CourierReadNested(BaseModel):
    id: int
    code: str
    name: str
    type: Literal["regular", "express", "same_day", "instant"]
    is_active: bool
    sort_order: int


class ShippingAddressReadNested(BaseModel):
    id: int
    courier_id: int
    sub_district_id: int
    type: Literal["regular", "express", "same_day", "instant"]
    price: float
    is_active: bool
    sort_order: int


# --- Courier Schemas ---
class CourierBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    type: Literal["regular", "express", "same_day", "instant"] = "regular"
    is_active: bool = True
    sort_order: int = 0


class Courier(CourierBase, TimestampSchema):
    id: int


class CourierCreate(CourierBase):
    pass


class CourierUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    type: Literal["regular", "express", "same_day", "instant"] | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CourierRead(CourierBase, TimestampSchema):
    id: int
    shipping_addresses: list[ShippingAddressReadNested] = []


# --- Shipping Address Schemas ---
class ShippingAddressBase(BaseModel):
    courier_id: int
    sub_district_id: int
    type: Literal["regular", "express", "same_day", "instant"] = "regular"
    price: float = 0.0
    is_active: bool = True
    sort_order: int = 0


class ShippingAddressCreate(ShippingAddressBase):
    pass


class ShippingAddressUpdate(BaseModel):
    courier_id: int | None = None
    sub_district_id: int | None = None
    type: Literal["regular", "express", "same_day", "instant"] | None = None
    price: float | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ShippingAddressRead(ShippingAddressBase, TimestampSchema):
    id: int
    courier: CourierReadNested | None = None
