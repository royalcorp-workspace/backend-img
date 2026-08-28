import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    pass


class Category(Base, TimestampMixin):
    __tablename__ = "product_category"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_category.id"), index=True, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    tagline: Mapped[str | None] = mapped_column(String(255), default=None)
    image: Mapped[str | None] = mapped_column(String(255), default=None)
    banner: Mapped[str | None] = mapped_column(String(255), default=None)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    status: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    creator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", back_populates="children", lazy="selectin", init=False
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", lazy="selectin", init=False
    )
