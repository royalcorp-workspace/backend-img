from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from ..customer.models import Customer
    from ..product.models import Product, ProductVariant


class Order(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=0)
    payment_method: Mapped[str | None] = mapped_column(String(50), default=None)
    payment_status: Mapped[str | None] = mapped_column(String(20), default=None)
    subtotal: Mapped[float | None] = mapped_column(default=0.0)
    tax: Mapped[float | None] = mapped_column(default=0.0)
    discount: Mapped[float | None] = mapped_column(default=0.0)
    total: Mapped[float | None] = mapped_column(default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    meta: Mapped[str | None] = mapped_column(Text, default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)

    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin", init=False)
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
    )


class OrderItem(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True, default=None)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[float] = mapped_column(default=0.0)
    discount: Mapped[float] = mapped_column(default=0.0)
    total: Mapped[float] = mapped_column(default=0.0)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)

    order: Mapped["Order"] = relationship("Order", back_populates="items", lazy="selectin", init=False)
    product: Mapped["Product"] = relationship("Product", lazy="selectin", init=False)
    variant: Mapped["ProductVariant | None"] = relationship("ProductVariant", lazy="selectin", init=False, default=None)
