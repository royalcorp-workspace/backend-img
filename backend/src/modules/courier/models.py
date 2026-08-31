import uuid as uuid_pkg
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from .courier import Courier


class Courier(Base, TimestampMixin):
    __tablename__ = "couriers"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[int | None] = mapped_column(Integer, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    shipping_addresses: Mapped[list["ShippingAddress"]] = relationship(
        "ShippingAddress",
        back_populates="courier",
        cascade="all, delete-orphan",
        init=False,
        lazy="selectin",
    )


class ShippingAddress(Base, TimestampMixin):
    __tablename__ = "shipping_addresses"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    courier_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("couriers.id"), nullable=False)
    sub_district_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    type: Mapped[int | None] = mapped_column(Integer, default=None)
    price: Mapped[float | None] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    courier: Mapped["Courier"] = relationship("Courier", back_populates="shipping_addresses", init=False)

    @property
    def type_name(self) -> str | None:
        mapping = {1: "reguler", 2: "express", 3: "same-day"}
        return mapping.get(self.type) if self.type else None
