from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from .crud import crud_permissions, crud_role_permissions, crud_user_roles
from .models import RBACRolePermission, RBACUserRole

logger = get_logger()


class RBACService:
    async def get_user_permissions(self, db: AsyncSession, user_id: int) -> set[str]:
        permissions = set()
        user_roles = await crud_user_roles.get_multi(db=db, filters={"user_id": user_id})
        for ur in user_roles.get("data", []):
            role_perms = await crud_role_permissions.get_multi(
                db=db, filters={"role_id": ur["role_id"]}
            )
            for rp in role_perms.get("data", []):
                perm = await crud_permissions.get(db=db, id=rp["permission_id"], is_deleted=False)
                if perm and perm.get("is_active", False):
                    permissions.add(perm["name"])
        return permissions

    async def user_has_permission(self, db: AsyncSession, user_id: int, permission: str) -> bool:
        perms = await self.get_user_permissions(db, user_id)
        return permission in perms

    async def assign_role_to_user(self, db: AsyncSession, user_id: int, role_id: int) -> None:
        existing = await crud_user_roles.get(db=db, user_id=user_id, role_id=role_id)
        if existing:
            return
        await crud_user_roles.create(db=db, object=RBACUserRole(user_id=user_id, role_id=role_id))

    async def assign_permission_to_role(self, db: AsyncSession, role_id: int, permission_id: int) -> None:
        existing = await crud_role_permissions.get(db=db, role_id=role_id, permission_id=permission_id)
        if existing:
            return
        await crud_role_permissions.create(
            db=db, object=RBACRolePermission(role_id=role_id, permission_id=permission_id)
        )


rbac_service = RBACService()
