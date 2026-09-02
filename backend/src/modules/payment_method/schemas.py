import uuid
from typing import Annotated, Any

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


class PaymentMethodBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    type: int | None = None
    type_name: str | None = None
    bank_name: str | None = None
    provider: str | None = None
    image: str | None = None
    has_charge: bool = False
    charge_type: int | None = None
    charge_value: float | None = 0.0
    charge_bearer: str | None = None
    minimum_amount: float | None = 0.0
    maximum_amount: float | None = None
    sort_order: int | None = 0
    status: int | None = 1
    bank_info: Any | None = None
    instructions: Any | None = None
    cara_bayar: list[str] | None = None


class PaymentMethod(PaymentMethodBase, TimestampSchema):
    id: uuid.UUID


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    type: int | None = None
    type_name: str | None = None
    bank_name: str | None = None
    provider: str | None = None
    image: str | None = None
    has_charge: bool | None = None
    charge_type: int | None = None
    charge_value: float | None = None
    charge_bearer: str | None = None
    minimum_amount: float | None = None
    maximum_amount: float | None = None
    sort_order: int | None = None
    status: int | None = None
    bank_info: Any | None = None
    instructions: Any | None = None
    cara_bayar: list[str] | None = None


class PaymentMethodRead(PaymentMethodBase, TimestampSchema):
    id: uuid.UUID
