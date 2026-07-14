from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from ..user.models import User


RoleUserAssociation = None


class Role(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "rbac_roles"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[list["User"]] = relationship(
        "User", secondary="rbac_user_roles", back_populates="roles", lazy="selectin", init=False
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="rbac_role_permissions",
        back_populates="roles",
        lazy="selectin",
        init=False,
    )


class Permission(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "rbac_permissions"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="rbac_role_permissions",
        back_populates="permissions",
        lazy="selectin",
        init=False,
    )


class RBACUserRole(Base):
    __tablename__ = "rbac_user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("rbac_roles.id"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), nullable=False, init=False
    )


class RBACRolePermission(Base):
    __tablename__ = "rbac_role_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("rbac_roles.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("rbac_permissions.id"), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), nullable=False, init=False
    )
