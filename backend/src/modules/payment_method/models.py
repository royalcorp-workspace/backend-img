import uuid
from typing import Any

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base


class PaymentMethod(Base, TimestampMixin):
    __tablename__ = "payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[int | None] = mapped_column(Integer, default=None)
    provider: Mapped[str | None] = mapped_column(String(100), default=None)
    image: Mapped[str | None] = mapped_column(String(255), default=None)
    has_charge: Mapped[bool] = mapped_column(Boolean, default=False)
    charge_type: Mapped[int | None] = mapped_column(Integer, default=None)
    charge_value: Mapped[float | None] = mapped_column(default=0.0)
    charge_bearer: Mapped[str | None] = mapped_column(String(50), default=None)
    minimum_amount: Mapped[float | None] = mapped_column(default=0.0)
    maximum_amount: Mapped[float | None] = mapped_column(default=None)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    status: Mapped[int | None] = mapped_column(Integer, default=1)
    bank_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    instructions: Mapped[dict[str, Any] | list[Any] | Any | None] = mapped_column(JSONB, default=None)
    creator: Mapped[str | None] = mapped_column(String(100), default=None)
    editor: Mapped[str | None] = mapped_column(String(100), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
