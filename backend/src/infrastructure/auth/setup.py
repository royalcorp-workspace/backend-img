"""crudauth composition root.

A single module-level ``auth`` singleton wired over the existing ``User`` model.
It is constructed here, not in the lifespan, because routers and ``current_user``
dependencies reference it at import time; the lifespan only opens and closes its
connections via ``auth.initialize()`` / ``auth.shutdown()`` (see ``app_factory``).

Wires a single session transport (sessions + CSRF + escalating login lockout)
over the configured session backend, plus a shared Redis rate limiter for the
lockout counters. Email recovery and sudo are intentionally not configured -
the boilerplate has no email pipeline, and no route gates on sudo.
"""

from crudauth import CookieConfig, CRUDAuth, SessionTransport
from crudauth.identity import IdentityConfig
from crudauth.ratelimit import redis_rate_limiter
from crudauth.transports.bearer import BearerTransport

from ...modules.user.models import User
from ..config.settings import settings
from ..database.session import async_session

_redis_password = settings.CACHE_REDIS_PASSWORD
_redis_auth = f":{_redis_password}@" if _redis_password else ""
_session_redis_url = f"redis://{_redis_auth}{settings.CACHE_REDIS_HOST}:{settings.CACHE_REDIS_PORT}/{settings.CACHE_REDIS_DB}"

_use_redis = settings.SESSION_BACKEND == "redis"

_bearer_transport = BearerTransport(
    access_ttl=3600,
    refresh_ttl_days=30,
    refresh="cookie",
)

# The existing 'users' table uses a different naming convention than the User model.
# Map crudauth logical fields to the actual database column names.
_user_column_map = {
    "hashed_password": "password",
    "is_superuser": "is_superuser",
}

_identity = IdentityConfig(
    login=["email"],
    recovery="email",
)

auth = CRUDAuth(
    session=async_session,
    user_model=User,
    SECRET_KEY=settings.SECRET_KEY,
    column_map=_user_column_map,
    identity=_identity,
    cookies=CookieConfig(secure=settings.SESSION_SECURE_COOKIES),
    transports=[
        SessionTransport(
            backend="redis" if _use_redis else "memory",
            redis_url=_session_redis_url if _use_redis else None,
            csrf=settings.CSRF_ENABLED,
            max_sessions_per_user=settings.MAX_SESSIONS_PER_USER,
            session_timeout_minutes=settings.SESSION_TIMEOUT_MINUTES,
            cleanup_interval_minutes=settings.SESSION_CLEANUP_INTERVAL_MINUTES,
        ),
        _bearer_transport,
    ],
    rate_limiter=redis_rate_limiter(redis_url=_session_redis_url) if _use_redis else None,
    trusted_proxy_hops=settings.TRUSTED_PROXY_HOPS,
)
