import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
import sqlalchemy.types as types
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base

class VoucherType(types.TypeDecorator):
    impl = types.SmallInteger
    cache_ok = True

    def process_bind_param(self, value, dialect):
        mapping = {"fixed": 1, "percentage": 2, "shipping_discount": 3, "free_gift": 4}
        if isinstance(value, str):
            return mapping.get(value, 2)
        return value

    def process_result_value(self, value, dialect):
        mapping = {1: "fixed", 2: "percentage", 3: "shipping_discount", 4: "free_gift"}
        if isinstance(value, int):
            return mapping.get(value, "percentage")
        return value

class VoucherScope(types.TypeDecorator):
    impl = types.SmallInteger
    cache_ok = True

    def process_bind_param(self, value, dialect):
        mapping = {"global": 1, "product": 2, "category": 3}
        if isinstance(value, str):
            return mapping.get(value, 1)
        return value

    def process_result_value(self, value, dialect):
        mapping = {1: "global", 2: "product", 3: "category"}
        if isinstance(value, int):
            return mapping.get(value, "global")
        return value

class Voucher(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vouchers"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        primary_key=True,
        default=uuid_pkg.uuid4,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    type: Mapped[str] = mapped_column(VoucherType, default="percentage")
    scope: Mapped[str] = mapped_column(VoucherScope, default="global")
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
