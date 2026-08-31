from sqlalchemy import text
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

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    remember_token: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    firebase_token: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    firebase_uid: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    auth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    creator: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    editor: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    customer_type: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1", default=1)
    membership_level: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    reseller_price_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    def __repr__(self) -> str:
        return f"{self.name} ({self.email})"

class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    user_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None, server_default=text("CURRENT_TIMESTAMP"))
