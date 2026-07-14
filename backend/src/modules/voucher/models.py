from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class Voucher(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    type: Mapped[str] = mapped_column(String(50), default="percentage")
    scope: Mapped[str] = mapped_column(String(50), default="global")
    allow_stacking: Mapped[bool] = mapped_column(Boolean, default=False)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    min_purchase: Mapped[float | None] = mapped_column(Float, default=0.0)
    max_discount: Mapped[float | None] = mapped_column(Float, default=None)
    usage_limit: Mapped[int | None] = mapped_column(Integer, default=None)
    usage_limit_per_user: Mapped[int | None] = mapped_column(Integer, default=None)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    valid_for_new_customer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
