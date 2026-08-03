from typing import Annotated, Any

from fastapi import Depends

from ...infrastructure.auth.dependencies import get_current_user
from ...infrastructure.dependencies import AsyncSessionDep
from ...infrastructure.logging import get_logger
from ..common.exceptions import PermissionDeniedError
from .service import rbac_service

logger = get_logger()


def require_permission(permission: str):
    async def _checker(
        current_user: Annotated[dict[str, Any], Depends(get_current_user)],
        db: AsyncSessionDep,
    ) -> dict[str, Any]:
        if current_user.get("is_superuser"):
            return current_user
        has_perm = await rbac_service.user_has_permission(
            db=db, user_id=current_user["id"], permission=permission
        )
        if not has_perm:
            logger.warning(
                "Permission denied",
                extra={"user_id": current_user.get("id"), "permission": permission},
            )
            raise PermissionDeniedError(f"Missing permission: {permission}")
        return current_user

    return _checker
