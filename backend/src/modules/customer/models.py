from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base
from ...modules.user.models import User


class Customer(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True, default=None)
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    meta: Mapped[str | None] = mapped_column(Text, default=None)

    user: Mapped["User | None"] = relationship("User", lazy="selectin", init=False)
    addresses: Mapped[list["Address"]] = relationship(
        "Address",
        back_populates="customer",
        cascade="all, delete-orphan",
        init=False,
        lazy="selectin",
    )


class Address(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(String(50), default="Rumah")
    postal_code: Mapped[str | None] = mapped_column(String(10), default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)

    customer: Mapped[Customer] = relationship("Customer", back_populates="addresses", init=False)
