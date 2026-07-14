from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class PaymentMethod(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="bank_transfer")
    provider: Mapped[str | None] = mapped_column(String(100), default=None)
    image: Mapped[str | None] = mapped_column(String(255), default=None)
    has_charge: Mapped[bool] = mapped_column(Boolean, default=False)
    charge_type: Mapped[str] = mapped_column(String(50), default="fixed")
    charge_value: Mapped[float] = mapped_column(Float, default=0.0)
    charge_bearer: Mapped[str] = mapped_column(String(50), default="customer")
    minimum_amount: Mapped[float | None] = mapped_column(Float, default=0.0)
    maximum_amount: Mapped[float | None] = mapped_column(Float, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
