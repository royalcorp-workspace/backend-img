import uuid
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field

from ..common.schemas import TimestampSchema


# --- Address Schemas ---
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
    model_config = {
        "json_schema_extra": {
            "example": {
                "label": "Rumah",
                "recipient_name": "Jane Doe",
                "phone": "+6281234567890",
                "address": "Jl. Hayam Wuruk No. 12, Gambir",
                "city_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "sub_district_id": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
                "postal_code": "10120",
                "is_primary": True,
            }
        }
    }


class AddressUpdate(BaseModel):
    id: uuid.UUID | None = Field(None, description="Address ID if updating an existing address")
    address_id: uuid.UUID | None = Field(None, description="Alternative field for Address ID")
    addresses_id: uuid.UUID | None = Field(None, description="Alternative field for Address ID")
    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    address: str | None = None
    city_id: uuid.UUID | None = None
    sub_district_id: uuid.UUID | None = None
    postal_code: str | None = None
    is_primary: bool | None = None


class AddressRead(AddressBase):
    id: uuid.UUID
    customer_id: uuid.UUID | None = None
    city_name: str | None = None
    sub_district_name: str | None = None
    district_name: str | None = None
    province_id: str | None = None
    province_name: str | None = None
    created_at: Any | None = None
    updated_at: Any | None = None


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
    addresses: list[AddressCreate] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "phone": "+6281234567890",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "meta": None,
                "addresses": [
                    {
                        "label": "Rumah",
                        "recipient_name": "Jane Doe",
                        "phone": "+6281234567890",
                        "address": "Jl. Hayam Wuruk No. 12, Gambir",
                        "city_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "sub_district_id": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "postal_code": "10120",
                        "is_primary": True,
                    }
                ],
            }
        }
    }


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    meta: str | None = None
    user_id: uuid.UUID | None = None
    addresses_id: uuid.UUID | None = Field(None, description="Optional Address ID if updating address directly")
    address_id: uuid.UUID | None = Field(None, description="Optional Address ID if updating address directly")
    addresses: list[AddressUpdate] | None = None
    address: AddressUpdate | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Jane Doe Updated",
                "email": "jane.updated@example.com",
                "phone": "+6281234567899",
                "meta": None,
                "addresses": [
                    {
                        "id": "223e4567-e89b-12d3-a456-426614174001",
                        "label": "Kantor",
                        "recipient_name": "Jane Doe",
                        "phone": "+6281234567899",
                        "address": "Jalan Sudirman Kav. 1, Gambir",
                        "city_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "sub_district_id": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "postal_code": "10120",
                        "is_primary": True,
                    }
                ],
            }
        }
    }


class CustomerRead(CustomerBase, TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    addresses: list[AddressRead] = []
