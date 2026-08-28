import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UUID, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base


class AboutUs(Base, TimestampMixin):
    __tablename__ = "about_us"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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


class BlogPost(Base, TimestampMixin):
    __tablename__ = "blog_posts"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(255), default=None)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    featured_image: Mapped[str | None] = mapped_column(String(255), default=None)
    author_name: Mapped[str | None] = mapped_column(String(255), default=None)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[str | None] = mapped_column(String(255), default=None)
    meta_description: Mapped[str | None] = mapped_column(String(255), default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class Faq(Base, TimestampMixin):
    __tablename__ = "faqs"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)


class HowToReturn(Base, TimestampMixin):
    __tablename__ = "how_to_returns"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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


class PrivacyPolicy(Base, TimestampMixin):
    __tablename__ = "privacy_policies"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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


class TermsAndCondition(Base, TimestampMixin):
    __tablename__ = "terms_and_conditions"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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


class WarrantyClaim(Base, TimestampMixin):
    __tablename__ = "warranty_claims"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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


class Banner(Base, TimestampMixin):
    __tablename__ = "banners"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    title: Mapped[str | None] = mapped_column(String(255), default=None)
    link_url: Mapped[str | None] = mapped_column(String(255), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[int] = mapped_column(Integer, default=1)
    device_flag: Mapped[int] = mapped_column(Integer, default=1)
    placement_size: Mapped[int] = mapped_column(Integer, default=1)
    content_type: Mapped[int] = mapped_column(Integer, default=1)
    image_web_url: Mapped[str | None] = mapped_column(String(500), default=None)
    image_mobile_url: Mapped[str | None] = mapped_column(String(500), default=None)
    embed_web_content: Mapped[str | None] = mapped_column(Text, default=None)
    embed_mobile_content: Mapped[str | None] = mapped_column(Text, default=None)
    target_type: Mapped[str | None] = mapped_column(String(255), default=None)
    target_id: Mapped[str | None] = mapped_column(String(36), default=None)


class HomepageSection(Base, TimestampMixin):
    __tablename__ = "homepage_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    section_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    event_type: Mapped[str] = mapped_column(String(255), default="mega_campaign")
    banner_image: Mapped[str | None] = mapped_column(String(255), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
    
    popups: Mapped[list["EventPopup"]] = relationship("EventPopup", back_populates="event", lazy="selectin", init=False)


class EventPopup(Base, TimestampMixin):
    __tablename__ = "event_popups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), default=None)
    image_url: Mapped[str | None] = mapped_column(String(255), default=None)
    link_url: Mapped[str | None] = mapped_column(String(255), default=None)
    button_text: Mapped[str | None] = mapped_column(String(100), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    event: Mapped["Event"] = relationship("Event", back_populates="popups", init=False)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, default=None)
    link_url: Mapped[str | None] = mapped_column(String(255), default=None)
    is_broadcast: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
