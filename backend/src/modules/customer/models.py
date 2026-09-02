import uuid

from sqlalchemy import UUID, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), default=None)
    # References the (externally managed) ``users`` table; kept as a plain UUID
    # column without a FK because that table is not modelled in this service.
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, default=None)
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    meta: Mapped[str | None] = mapped_column(Text, default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)


class Address(Base, TimestampMixin):
    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    city_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, default=None)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, default=None)
    sub_district_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    postal_code: Mapped[str | None] = mapped_column(String(10), default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
