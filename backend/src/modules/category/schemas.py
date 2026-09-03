from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..common.schemas import TimestampSchema
from ..common.utils import get_media_url


class CategoryBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    slug: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")]
    parent_id: UUID | None = None
    description: str | None = None
    image: str | None = None
    banner_web: str | None = None
    banner_mobile: str | None = None
    tagline: str | None = None
    sort_order: int | None = 0
    status: bool = True

    @field_validator("image", "banner_web", "banner_mobile", mode="before")
    @classmethod
    def format_category_images(cls, v: Any) -> Any:
        return get_media_url(v)


class Category(CategoryBase, TimestampSchema):
    id: UUID


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    parent_id: UUID | None = None
    description: str | None = None
    image: str | None = None
    banner_web: str | None = None
    banner_mobile: str | None = None
    tagline: str | None = None
    sort_order: int | None = None
    status: bool | None = None


class CategoryRead(CategoryBase):
    id: UUID
