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
        # RBAC is bypassed for now as per user request (backend is only for customers)
        return current_user

    return _checker
