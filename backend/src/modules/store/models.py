import uuid

from sqlalchemy import JSON, UUID, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base


class StoreGroup(Base, TimestampMixin):
    __tablename__ = "store_group"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    stores: Mapped[list["Store"]] = relationship(
        "Store",
        back_populates="group",
        cascade="all, delete-orphan",
        init=False,
        lazy="selectin",
    )


class StoreTier(Base, TimestampMixin):
    __tablename__ = "store_tier"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    level: Mapped[int] = mapped_column(Integer, default=1)
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    stores: Mapped[list["Store"]] = relationship(
        "Store",
        back_populates="tier",
        cascade="all, delete-orphan",
        init=False,
        lazy="selectin",
    )


class StoreChannelGroup(Base, TimestampMixin):
    __tablename__ = "store_channel_group"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    channels: Mapped[list["StoreChannel"]] = relationship(
        "StoreChannel",
        back_populates="channel_group",
        cascade="all, delete-orphan",
        init=False,
        lazy="selectin",
    )


class Store(Base, TimestampMixin):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    store_group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("store_group.id"), nullable=False)
    tier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("store_tier.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)
    outstanding_balance: Mapped[float] = mapped_column(Float, default=0.0)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    email: Mapped[str | None] = mapped_column(String(100), default=None)
    documents: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    payment_term: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    group: Mapped[StoreGroup] = relationship("StoreGroup", back_populates="stores", init=False, lazy="selectin")
    tier: Mapped[StoreTier] = relationship("StoreTier", back_populates="stores", init=False, lazy="selectin")
    channels: Mapped[list["StoreChannel"]] = relationship(
        "StoreChannel",
        back_populates="store",
        cascade="all, delete-orphan",
        init=False,
        lazy="selectin",
    )


class StoreChannel(Base, TimestampMixin):
    __tablename__ = "store_channel"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    store_channel_group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("store_channel_group.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    store: Mapped[Store] = relationship("Store", back_populates="channels", init=False, lazy="selectin")
    channel_group: Mapped[StoreChannelGroup] = relationship(
        "StoreChannelGroup", back_populates="channels", init=False, lazy="selectin"
    )
