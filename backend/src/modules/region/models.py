import uuid as uuid_pkg
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base

class Province(Base, TimestampMixin):
    __tablename__ = "provinces"
    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4, init=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20), unique=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(255), default=None)
    editor: Mapped[str | None] = mapped_column(String(255), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

class City(Base, TimestampMixin):
    __tablename__ = "cities"
    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4, init=False
    )
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    province_id: Mapped[str | None] = mapped_column(String(255), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(255), default=None)
    editor: Mapped[str | None] = mapped_column(String(255), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)

class SubDistrict(Base, TimestampMixin):
    __tablename__ = "sub_districts"
    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4, init=False
    )
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    city_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    sub_district: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False)
    province_id: Mapped[str | None] = mapped_column(String(255), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[str | None] = mapped_column(String(255), default=None)
    editor: Mapped[str | None] = mapped_column(String(255), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, init=False)
