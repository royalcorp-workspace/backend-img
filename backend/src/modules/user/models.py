import uuid as uuid_pkg
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    pass


class User(Base):
    """User model representing application users."""

    __tablename__ = "users"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    remember_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    firebase_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    editor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    customer_type: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1", default=1)
    membership_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reseller_price_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deleted_at: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"{self.name} ({self.email})"
