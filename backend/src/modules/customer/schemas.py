from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from ..common.schemas import TimestampSchema


# --- Address Schemas ---
class AddressBase(BaseModel):
    label: str = "Rumah"
    recipient_name: str
    phone: str
    address: str
    postal_code: str | None = None
    is_primary: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    address: str | None = None
    postal_code: str | None = None
    is_primary: bool | None = None


class AddressRead(AddressBase, TimestampSchema):
    id: int
    customer_id: int


# --- Customer Schemas ---
class CustomerBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: Annotated[EmailStr, Field(max_length=100)]
    phone: str | None = None
    meta: str | None = None


class Customer(CustomerBase, TimestampSchema):
    id: int
    user_id: int | None = None


class CustomerCreate(CustomerBase):
    addresses: list[AddressCreate] = []


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    meta: str | None = None
    addresses: list[AddressCreate] | None = None


class CustomerRead(CustomerBase, TimestampSchema):
    id: int
    user_id: int | None = None
    addresses: list[AddressRead] = []
