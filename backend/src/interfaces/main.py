from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from ..infrastructure.app_factory import create_application, lifespan_factory
from ..infrastructure.config.settings import get_settings
from ..infrastructure.security import validate_production_security
from ..interfaces.api import router
from .admin.initialize import create_admin_interface

settings = get_settings()


@asynccontextmanager
async def lifespan_with_security(app: FastAPI) -> AsyncGenerator[None, None]:
    """Custom lifespan that includes security validation."""
    if settings.PRODUCTION_SECURITY_VALIDATION_ENABLED:
        validate_production_security(settings)

    default_lifespan = lifespan_factory(settings, create_tables_on_startup=settings.CREATE_TABLES_ON_STARTUP)

    async with default_lifespan(app):
        yield


app = create_application(
    router=router,
    settings=settings,
    lifespan=lifespan_with_security,
    create_tables_on_startup=None,
    enable_cors=None,
    cors_origins=None,
    enable_docs_in_production=None,
    docs_production_dependency=None,
    enable_gzip=None,
    openapi_prefix=None,
    title="Backend IMG Store",
    summary="A modular FastAPI starter with a plugin system",
    description="""
    # Backend IMG Store

    Available features:

    * Account & Login
    * Users
    * API Keys
    * Categories
    * Customers
    * Products
    * Inventory
    * Orders
    * Vouchers
    * Reviews
    * Membership Tiers
    * Rate Limiting
    * Couriers
    * Payment Methods
    * Stores & Channels (Groups, Tiers, Channel Groups)
    * Shipping Address Rates
    * Web Content (About Us, Blog, FAQ, How To Return, Privacy, Terms, Warranty)
    * Admin Panel
    """,
    version="0.19.0",
    openapi_tags=None,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
create_admin_interface(app)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy"}


