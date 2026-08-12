from uuid import UUID
from datetime import datetime
from typing import Annotated, Literal, Any

from pydantic import BaseModel, Field, field_validator

from ..common.schemas import TimestampSchema


class VoucherBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    title: Annotated[str, Field(min_length=1, max_length=150)]
    description: str | None = None
    type: Literal["percentage", "fixed", "shipping_discount", "free_gift"] = "percentage"
    scope: Literal["global", "product", "category"] = "global"

    @field_validator("type", mode="before")
    @classmethod
    def map_type(cls, v: Any) -> str:
        if isinstance(v, int):
            return {1: "fixed", 2: "percentage", 3: "shipping_discount", 4: "free_gift"}.get(v, "percentage")
        return v

    @field_validator("scope", mode="before")
    @classmethod
    def map_scope(cls, v: Any) -> str:
        if isinstance(v, int):
            return {1: "global", 2: "product", 3: "category"}.get(v, "global")
        return v
    allow_stacking: bool = False
    value: float = 0.0
    min_purchase: float | None = 0.0
    max_discount: float | None = None
    usage_limit: int | None = None
    usage_limit_per_user: int | None = None
    used_count: int = 0
    start_date: datetime
    end_date: datetime
    valid_for_new_customer: bool = False
    is_active: bool = True


class Voucher(VoucherBase, TimestampSchema):
    id: UUID


class VoucherCreate(VoucherBase):
    pass


class VoucherUpdate(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    type: Literal["percentage", "fixed", "shipping_discount", "free_gift"] | None = None
    scope: Literal["global", "product", "category"] | None = None
    allow_stacking: bool | None = None
    value: float | None = None
    min_purchase: float | None = None
    max_discount: float | None = None
    usage_limit: int | None = None
    usage_limit_per_user: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    valid_for_new_customer: bool | None = None
    is_active: bool | None = None


class VoucherRead(VoucherBase):
    id: UUID
