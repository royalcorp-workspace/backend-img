from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class Courier(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "couriers"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="regular")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)

    shipping_addresses: Mapped[list["ShippingAddress"]] = relationship(
        "ShippingAddress",
        back_populates="courier",
        cascade="all, delete-orphan",
        init=False,
        lazy="selectin",
    )


class ShippingAddress(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "shipping_addresses"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    courier_id: Mapped[int] = mapped_column(ForeignKey("couriers.id", ondelete="CASCADE"), nullable=False)
    sub_district_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="regular")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)

    courier: Mapped[Courier] = relationship("Courier", back_populates="shipping_addresses", init=False)
