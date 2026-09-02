import uuid as uuid_pkg
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from ..customer.models import Customer
    from ..product.models import Product, ProductVariant


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    customer_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=0)
    payment_method: Mapped[str | None] = mapped_column(String(50), default=None)
    payment_status: Mapped[int | None] = mapped_column(Integer, default=None)
    subtotal: Mapped[float | None] = mapped_column(default=0.0)
    tax: Mapped[float | None] = mapped_column(default=0.0)
    discount: Mapped[float | None] = mapped_column(default=0.0)
    total: Mapped[float | None] = mapped_column(default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    
    order_number: Mapped[str | None] = mapped_column(String(255), default=None)
    voucher_id: Mapped[uuid_pkg.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vouchers.id"), default=None)
    transaction_fee: Mapped[float | None] = mapped_column(default=0.0)
    courier_id: Mapped[uuid_pkg.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    voucher_nominal: Mapped[float | None] = mapped_column(default=0.0)
    shipping_cost: Mapped[float | None] = mapped_column(default=0.0)
    shipping_cost_subsidy: Mapped[float | None] = mapped_column(default=0.0)
    shipping_addresses_id: Mapped[uuid_pkg.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    settlement_id: Mapped[uuid_pkg.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin", init=False)
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
    )


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    order_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
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
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float | None] = mapped_column(default=0.0)
    discount_nominal: Mapped[float | None] = mapped_column(default=0.0)
    discount_percent: Mapped[float | None] = mapped_column(default=0.0)
    total: Mapped[float | None] = mapped_column(default=0.0)
    name: Mapped[str | None] = mapped_column(String(255), default=None)
    item_notes: Mapped[str | None] = mapped_column(Text, default=None)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)

    order: Mapped["Order"] = relationship("Order", back_populates="items", lazy="selectin", init=False)
    product: Mapped["Product"] = relationship("Product", lazy="selectin", init=False)
    variant: Mapped["ProductVariant | None"] = relationship("ProductVariant", lazy="selectin", init=False)


class VoidOrder(Base, TimestampMixin):
    __tablename__ = "void_orders"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    order_number: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    customer_id: Mapped[uuid_pkg.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        default=None,
        index=True,
    )
    order_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    order_items_data: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB, default=None)
    void_reason: Mapped[str | None] = mapped_column(Text, default=None)
    voided_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), default=None)


OrderVoid = VoidOrder
