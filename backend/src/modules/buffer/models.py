import uuid as uuid_pkg
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from ..customer.models import Customer
    from ..product.models import Product, ProductVariant


class Buffer(Base, TimestampMixin):
    __tablename__ = "buffers"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    customer_id: Mapped[uuid_pkg.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=True,
        default=None,
    )
    session_id: Mapped[str | None] = mapped_column(String(100), default=None)
    customer_name: Mapped[str | None] = mapped_column(String(255), default=None)
    customer_email: Mapped[str | None] = mapped_column(String(255), default=None)
    customer_phone: Mapped[str | None] = mapped_column(String(50), default=None)
    subtotal: Mapped[float | None] = mapped_column(default=0.0)
    tax: Mapped[float | None] = mapped_column(default=0.0)
    discount: Mapped[float | None] = mapped_column(default=0.0)
    total: Mapped[float | None] = mapped_column(default=0.0)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    creator: Mapped[uuid_pkg.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid_pkg.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)

    customer: Mapped["Customer | None"] = relationship("Customer", lazy="selectin", init=False)
    items: Mapped[list["BufferItem"]] = relationship(
        "BufferItem",
        back_populates="buffer",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
    )


class BufferItem(Base, TimestampMixin):
    __tablename__ = "buffer_items"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    buffer_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buffers.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=False,
    )
    product_variant_id: Mapped[uuid_pkg.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id"),
        nullable=True,
        default=None,
    )
    name: Mapped[str | None] = mapped_column(String(255), default=None)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float | None] = mapped_column(default=0.0)
    total: Mapped[float | None] = mapped_column(default=0.0)
    discount_nominal: Mapped[float | None] = mapped_column(default=0.0)
    discount_percent: Mapped[float | None] = mapped_column(default=0.0)
    item_notes: Mapped[str | None] = mapped_column(Text, default=None)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)

    buffer: Mapped["Buffer"] = relationship("Buffer", back_populates="items", lazy="selectin", init=False)
    product: Mapped["Product"] = relationship("Product", lazy="selectin", init=False)
    variant: Mapped["ProductVariant | None"] = relationship("ProductVariant", lazy="selectin", init=False, default=None)
