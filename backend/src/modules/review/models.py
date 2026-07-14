from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from .product import Product


class Review(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(Integer, default=None)
    user_name: Mapped[str | None] = mapped_column(String(100), default=None)
    user_email: Mapped[str | None] = mapped_column(String(100), default=None)
    rating: Mapped[int | None] = mapped_column(Integer, default=0)
    text: Mapped[str | None] = mapped_column(Text, default=None)
    image_url: Mapped[str | None] = mapped_column(String(255), default=None)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    report_count: Mapped[int | None] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship("Product", back_populates="reviews", lazy="selectin", init=False)
