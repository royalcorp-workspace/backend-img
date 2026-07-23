"""SQLAdmin interface initialization."""

import os

from sqladmin import Admin

from ...infrastructure.config.settings import get_settings
from ...infrastructure.database.session import engine
from .auth import AdminAuth
from .views import register_admin_views

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "templates"
)


def create_admin_interface(app) -> Admin | None:
    """Create and configure the SQLAdmin interface.

    Args:
        app: The FastAPI application instance.

    Returns:
        Configured Admin instance or None if admin is disabled.
    """
    settings = get_settings()

    if not settings.ADMIN_ENABLED:
        return None

    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)

    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        title="Admin",
        templates_dir=TEMPLATES_DIR,
    )

    register_admin_views(admin)

    return admin
