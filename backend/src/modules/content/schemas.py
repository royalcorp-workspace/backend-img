from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from ..common.schemas import TimestampSchema


# --- About Us ---
class AboutUsBase(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    tagline: str | None = None
    description: str | None = None
    vision: str | None = None
    mission: str | None = None
    values: str | None = None
    established_year: int | None = None
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    logo: str | None = None
    cover_image: str | None = None
    social_media: dict[str, Any] | None = None
    is_active: bool = True
    sort_order: int = 0


class AboutUsCreate(AboutUsBase):
    pass


class AboutUsUpdate(BaseModel):
    company_name: str | None = None
    tagline: str | None = None
    description: str | None = None
    vision: str | None = None
    mission: str | None = None
    values: str | None = None
    established_year: int | None = None
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    logo: str | None = None
    cover_image: str | None = None
    social_media: dict[str, Any] | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class AboutUsRead(AboutUsBase, TimestampSchema):
    id: int


# --- Blog Post ---
class BlogPostBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    excerpt: str | None = None
    content: str | None = None
    featured_image: str | None = None
    author_name: str | None = None
    is_published: bool = False
    is_featured: bool = False
    published_at: datetime | None = None
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None


class BlogPostCreate(BlogPostBase):
    pass


class BlogPostUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    excerpt: str | None = None
    content: str | None = None
    featured_image: str | None = None
    author_name: str | None = None
    is_published: bool | None = None
    is_featured: bool | None = None
    published_at: datetime | None = None
    sort_order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class BlogPostRead(BlogPostBase, TimestampSchema):
    id: int


# --- FAQ ---
class FaqBase(BaseModel):
    question: str
    answer: str
    sort_order: int = 0
    is_published: bool = True
    view_count: int = 0


class FaqCreate(FaqBase):
    pass


class FaqUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    sort_order: int | None = None
    is_published: bool | None = None
    view_count: int | None = None


class FaqRead(FaqBase, TimestampSchema):
    id: int


# --- How To Return ---
class HowToReturnBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    content: str | None = None
    steps: list[Any] | None = None
    featured_image: str | None = None
    is_published: bool = True
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None


class HowToReturnCreate(HowToReturnBase):
    pass


class HowToReturnUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content: str | None = None
    steps: list[Any] | None = None
    featured_image: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class HowToReturnRead(HowToReturnBase, TimestampSchema):
    id: int


# --- Privacy Policy ---
class PrivacyPolicyBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    content: str | None = None
    version: str | None = None
    effective_date: datetime | None = None
    is_published: bool = True
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None


class PrivacyPolicyCreate(PrivacyPolicyBase):
    pass


class PrivacyPolicyUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content: str | None = None
    version: str | None = None
    effective_date: datetime | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class PrivacyPolicyRead(PrivacyPolicyBase, TimestampSchema):
    id: int


# --- Terms and Condition ---
class TermsAndConditionBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    content: str | None = None
    version: str | None = None
    effective_date: datetime | None = None
    is_published: bool = True
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None


class TermsAndConditionCreate(TermsAndConditionBase):
    pass


class TermsAndConditionUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content: str | None = None
    version: str | None = None
    effective_date: datetime | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class TermsAndConditionRead(TermsAndConditionBase, TimestampSchema):
    id: int


# --- Warranty Claim ---
class WarrantyClaimBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    content: str | None = None
    steps: list[Any] | None = None
    required_documents: list[Any] | None = None
    processing_time_days: int | None = None
    featured_image: str | None = None
    is_published: bool = True
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None


class WarrantyClaimCreate(WarrantyClaimBase):
    pass


class WarrantyClaimUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content: str | None = None
    steps: list[Any] | None = None
    required_documents: list[Any] | None = None
    processing_time_days: int | None = None
    featured_image: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class WarrantyClaimRead(WarrantyClaimBase, TimestampSchema):
    id: int
