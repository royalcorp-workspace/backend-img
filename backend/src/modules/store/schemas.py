import uuid
from typing import Annotated

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


# --- Nested Read Schemas (to avoid circular dependencies) ---
class StoreGroupReadNested(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    status: bool
    sort_order: int


class StoreTierReadNested(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    level: int
    credit_limit: float
    status: bool
    sort_order: int


class StoreChannelGroupReadNested(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    status: bool
    sort_order: int


class StoreReadNested(BaseModel):
    id: uuid.UUID
    store_group_id: uuid.UUID
    tier_id: uuid.UUID | None = None
    code: str
    name: str
    owner_user_id: uuid.UUID | None = None
    credit_limit: float
    outstanding_balance: float
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    documents: list[str] | None = None
    payment_term: int
    status: bool
    sort_order: int


class StoreChannelReadNested(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    store_channel_group_id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    status: bool
    sort_order: int


# --- Store Group ---
class StoreGroupBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    status: bool = True
    sort_order: int = 0


class StoreGroupCreate(StoreGroupBase):
    pass


class StoreGroupUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: bool | None = None
    sort_order: int | None = None


class StoreGroupRead(StoreGroupBase, TimestampSchema):
    id: uuid.UUID
    stores: list[StoreReadNested] = []


# --- Store Tier ---
class StoreTierBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    level: int = 1
    credit_limit: float = 0.0
    status: bool = True
    sort_order: int = 0


class StoreTierCreate(StoreTierBase):
    pass


class StoreTierUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    level: int | None = None
    credit_limit: float | None = None
    status: bool | None = None
    sort_order: int | None = None


class StoreTierRead(StoreTierBase, TimestampSchema):
    id: uuid.UUID
    stores: list[StoreReadNested] = []


# --- Store Channel Group ---
class StoreChannelGroupBase(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    status: bool = True
    sort_order: int = 0


class StoreChannelGroupCreate(StoreChannelGroupBase):
    pass


class StoreChannelGroupUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: bool | None = None
    sort_order: int | None = None


class StoreChannelGroupRead(StoreChannelGroupBase, TimestampSchema):
    id: uuid.UUID
    channels: list[StoreChannelReadNested] = []


# --- Store ---
class StoreBase(BaseModel):
    store_group_id: uuid.UUID
    tier_id: uuid.UUID | None = None
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=150)]
    owner_user_id: uuid.UUID | None = None
    credit_limit: float = 0.0
    outstanding_balance: float = 0.0
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    documents: list[str] | None = None
    payment_term: int = 0
    status: bool = True
    sort_order: int = 0


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    store_group_id: uuid.UUID | None = None
    tier_id: uuid.UUID | None = None
    code: str | None = None
    name: str | None = None
    owner_user_id: uuid.UUID | None = None
    credit_limit: float | None = None
    outstanding_balance: float | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    documents: list[str] | None = None
    payment_term: int | None = None
    status: bool | None = None
    sort_order: int | None = None


class StoreRead(StoreBase, TimestampSchema):
    id: uuid.UUID
    group: StoreGroupReadNested | None = None
    tier: StoreTierReadNested | None = None
    channels: list[StoreChannelReadNested] = []


# --- Store Channel ---
class StoreChannelBase(BaseModel):
    store_id: uuid.UUID
    store_channel_group_id: uuid.UUID
    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    status: bool = True
    sort_order: int = 0


class StoreChannelCreate(StoreChannelBase):
    pass


class StoreChannelUpdate(BaseModel):
    store_id: uuid.UUID | None = None
    store_channel_group_id: uuid.UUID | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: bool | None = None
    sort_order: int | None = None


class StoreChannelRead(StoreChannelBase, TimestampSchema):
    id: uuid.UUID
    store: StoreReadNested | None = None
    channel_group: StoreChannelGroupReadNested | None = None
