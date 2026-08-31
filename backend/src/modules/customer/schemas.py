import uuid
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field

from ..common.schemas import TimestampSchema


# --- Address Schemas ---
# NOTE: ``addresses`` in this database are user-scoped (linked via ``user_id`` and
# require a ``city_id``); they are not owned by customers.
class AddressBase(BaseModel):
    label: str = "Rumah"
    recipient_name: str
    phone: str
    address: str
    city_id: uuid.UUID
    user_id: uuid.UUID | None = None
    sub_district_id: uuid.UUID | None = None
    postal_code: str | None = None
    is_primary: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    address: str | None = None
    city_id: uuid.UUID | None = None
    sub_district_id: uuid.UUID | None = None
    postal_code: str | None = None
    is_primary: bool | None = None


class AddressRead(AddressBase, TimestampSchema):
    id: uuid.UUID


# --- Customer Schemas ---
class CustomerBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: Annotated[EmailStr, Field(max_length=100)] | None = None
    phone: str | None = None
    meta: str | None = None


class Customer(CustomerBase, TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None = None


class CustomerCreate(CustomerBase):
    user_id: uuid.UUID | None = None
    addresses: list["AddressCreate"] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Budi Santoso",
                "email": "budi@santoso.com",
                "phone": "0812345678",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "meta": None,
                "addresses": [
                    {
                        "label": "Rumah",
                        "recipient_name": "Budi",
                        "phone": "0812345678",
                        "address": "Jalan Kemerdekaan No. 17",
                        "city_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "sub_district_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "postal_code": "12345",
                        "is_primary": True
                    }
                ]
            }
        }
    }


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    meta: str | None = None
    user_id: uuid.UUID | None = None
    addresses: list["AddressCreate"] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Budi Santoso Updated",
                "email": "budi_new@santoso.com",
                "phone": "08123456789",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "meta": None,
                "addresses": [
                    {
                        "label": "Kantor",
                        "recipient_name": "Budi Santoso",
                        "phone": "08123456789",
                        "address": "Jalan Sudirman Kav. 1",
                        "city_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "sub_district_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "postal_code": "12190",
                        "is_primary": False
                    }
                ]
            }
        }
    }


class CustomerRead(CustomerBase, TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    addresses: list[dict[str, Any]] = []
