from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema

PaymentMethodType = Literal[
    "bank_transfer",
    "virtual_account",
    "ewallet",
    "qris",
    "credit_card",
    "debit_card",
    "cod",
    "paylater",
]
ChargeType = Literal["percentage", "fixed"]
ChargeBearer = Literal["customer", "merchant"]


class PaymentMethodBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    type: PaymentMethodType = "bank_transfer"
    provider: str | None = None
    image: str | None = None
    has_charge: bool = False
    charge_type: ChargeType = "fixed"
    charge_value: float = 0.0
    charge_bearer: ChargeBearer = "customer"
    minimum_amount: float | None = 0.0
    maximum_amount: float | None = None
    sort_order: int = 0
    status: bool = True


class PaymentMethod(PaymentMethodBase, TimestampSchema):
    id: int


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    type: PaymentMethodType | None = None
    provider: str | None = None
    image: str | None = None
    has_charge: bool | None = None
    charge_type: ChargeType | None = None
    charge_value: float | None = None
    charge_bearer: ChargeBearer | None = None
    minimum_amount: float | None = None
    maximum_amount: float | None = None
    sort_order: int | None = None
    status: bool | None = None


class PaymentMethodRead(PaymentMethodBase, TimestampSchema):
    id: int
