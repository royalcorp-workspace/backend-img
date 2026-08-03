import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from sqlalchemy import select  # noqa: E402

from src.infrastructure.database.session import local_session  # noqa: E402
from src.infrastructure.logging import get_logger  # noqa: E402
from src.modules.rbac.crud import crud_permissions, crud_role_permissions  # noqa: E402
from src.modules.rbac.models import Permission, RBACRolePermission, Role  # noqa: E402

logger = get_logger()


ADD_TO_CART_PERMISSIONS = [
    {"name": "add_to_cart:read", "action": "read", "subject": "add_to_cart", "description": "View add to cart"},
    {"name": "add_to_cart:create", "action": "create", "subject": "add_to_cart", "description": "Create add to cart"},
    {"name": "add_to_cart:update", "action": "update", "subject": "add_to_cart", "description": "Update add to cart"},
    {"name": "add_to_cart:delete", "action": "delete", "subject": "add_to_cart", "description": "Delete add to cart"},
]


async def seed_add_to_cart_permissions() -> None:
    async with local_session() as session:
        created_perms = {}
        for perm_data in ADD_TO_CART_PERMISSIONS:
            existing = await crud_permissions.get(db=session, name=perm_data["name"], is_deleted=False)
            if existing:
                logger.info(f"Permission '{perm_data['name']}' already exists.")
                created_perms[perm_data["name"]] = existing
            else:
                perm = Permission(**perm_data)
                session.add(perm)
                await session.flush()
                created_perms[perm_data["name"]] = {
                    "id": perm.id,
                    "name": perm.name,
                    "action": perm.action,
                    "subject": perm.subject,
                }
                logger.info(f"Created permission '{perm_data['name']}'")

        await session.commit()

        result = await session.execute(select(Role).where(Role.is_deleted == False))
        roles = result.scalars().all()

        if not roles:
            logger.warning("No roles found. Skipping role-permission assignment.")
            return

        for role in roles:
            for perm_name, perm in created_perms.items():
                perm_id = perm["id"] if isinstance(perm, dict) else perm["id"]
                existing_rp = await crud_role_permissions.get(
                     db=session, role_id=role.id, permission_id=perm_id
                )
                if not existing_rp:
                    rp = RBACRolePermission(role_id=role.id, permission_id=perm_id)
                    session.add(rp)
                    logger.info(f"Assigned '{perm_name}' to role '{role.name}'")
                else:
                    logger.info(f"Role '{role.name}' already has '{perm_name}'")

        await session.commit()
        logger.info("Add to Cart permissions seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_add_to_cart_permissions())
