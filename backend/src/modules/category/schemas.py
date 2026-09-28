from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from ..common.schemas import TimestampSchema
from ..common.utils import get_media_url


class CategoryBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    slug: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")]
    parent_id: UUID | None = None
    description: str | None = None
    tagline: str | None = None
    image: str | None = None
    banner_web: str | None = None
    banner_mobile: str | None = None
    sort_order: int | None = 0
    status: bool = True
    courier_setting_type: str | None = "detail"
    courier_type: str | None = "keduanya"

    @field_validator("image", "banner_web", "banner_mobile", mode="before", check_fields=False)
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
    tagline: str | None = None
    image: str | None = None
    banner_web: str | None = None
    banner_mobile: str | None = None
    sort_order: int | None = None
    status: bool | None = None
    courier_setting_type: str | None = None
    courier_type: str | None = None


class CategoryRead(CategoryBase, TimestampSchema):
    id: UUID
    logo: str | None = None
    banner: str | None = None
    is_featured: bool | None = False

    @model_validator(mode="before")
    @classmethod
    def set_computed_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = data.copy()
            if not data.get("banner"):
                data["banner"] = data.get("banner_web") or data.get("banner_mobile")
            if not data.get("logo"):
                data["logo"] = data.get("image")
        elif hasattr(data, "__dict__"):
            if not getattr(data, "banner", None):
                setattr(data, "banner", getattr(data, "banner_web", None) or getattr(data, "banner_mobile", None))
            if not getattr(data, "logo", None):
                setattr(data, "logo", getattr(data, "image", None))
        return data

    @field_validator("logo", "banner", mode="before", check_fields=False)
    @classmethod
    def format_additional_images(cls, v: Any) -> Any:
        return get_media_url(v)
