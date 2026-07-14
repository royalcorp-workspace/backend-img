from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


class CategoryBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    slug: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")]
    parent_id: UUID | None = None
    description: str | None = None
    sort_order: int | None = 0
    status: bool = True


class Category(CategoryBase, TimestampSchema):
    id: UUID


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    parent_id: UUID | None = None
    description: str | None = None
    sort_order: int | None = None
    status: bool | None = None


class CategoryRead(CategoryBase):
    id: UUID
