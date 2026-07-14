from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class AboutUs(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "about_us"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tagline: Mapped[str | None] = mapped_column(String(255), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    vision: Mapped[str | None] = mapped_column(Text, default=None)
    mission: Mapped[str | None] = mapped_column(Text, default=None)
    values: Mapped[str | None] = mapped_column(Text, default=None)
    established_year: Mapped[int | None] = mapped_column(Integer, default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    phone: Mapped[str | None] = mapped_column(String(50), default=None)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    logo: Mapped[str | None] = mapped_column(Text, default=None)
    cover_image: Mapped[str | None] = mapped_column(Text, default=None)
    social_media: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class BlogPost(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(255), default=None)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    featured_image: Mapped[str | None] = mapped_column(String(255), default=None)
    author_name: Mapped[str | None] = mapped_column(String(255), default=None)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[str | None] = mapped_column(String(255), default=None)
    meta_description: Mapped[str | None] = mapped_column(String(255), default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class Faq(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class HowToReturn(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "how_to_returns"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    steps: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    featured_image: Mapped[str | None] = mapped_column(String(255), default=None)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[str | None] = mapped_column(String(255), default=None)
    meta_description: Mapped[str | None] = mapped_column(String(255), default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class PrivacyPolicy(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "privacy_policies"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    version: Mapped[str | None] = mapped_column(String(50), default=None)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[str | None] = mapped_column(String(255), default=None)
    meta_description: Mapped[str | None] = mapped_column(String(255), default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class TermsAndCondition(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "terms_and_conditions"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    version: Mapped[str | None] = mapped_column(String(50), default=None)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[str | None] = mapped_column(String(255), default=None)
    meta_description: Mapped[str | None] = mapped_column(String(255), default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class WarrantyClaim(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "warranty_claims"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    steps: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    required_documents: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    processing_time_days: Mapped[int | None] = mapped_column(Integer, default=None)
    featured_image: Mapped[str | None] = mapped_column(String(255), default=None)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[str | None] = mapped_column(String(255), default=None)
    meta_description: Mapped[str | None] = mapped_column(String(255), default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
