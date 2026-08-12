from typing import Annotated, Any

from crudauth import Principal
from crudauth.exceptions import UnauthorizedException
from crudauth.oauth import OAuthState
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ...modules.customer.crud import crud_addresses, crud_customers
from ...modules.customer.schemas import AddressRead, CustomerRead
from ...modules.rbac.crud import crud_roles
from ...modules.rbac.service import rbac_service
from ...modules.user.crud import crud_users
from ...modules.user.enums import OAuthProvider
from ...modules.user.firebase_auth import verify_firebase_id_token
from ...modules.user.schemas import UserCreateInternal
from ..dependencies import AsyncSessionDep
from ..logging import get_logger
from .dependencies import get_current_principal, get_optional_principal
from .oauth import OAUTH_STATE_TTL_SECONDS, oauth_account_service, oauth_providers, oauth_state_storage
from .setup import _bearer_transport
from .setup import auth as crud_auth

logger = get_logger()

router = APIRouter(tags=["Authentication"])


class LoginForm(BaseModel):
    """Login request body - accepts both form-data and JSON."""
    email: str = Field(..., description="User email or username")
    password: str = Field(..., description="User password")


@router.post(
    "/login",
    summary="User Login",
    description="""
            Authenticates a user and creates a new session.

            This endpoint accepts username/email and password credentials and verifies them.
            On successful authentication:
            - A new session is created
            - A session ID is set as an HTTP-only cookie
            - A CSRF token is generated for protection against CSRF attacks
            - A bearer access token is issued for authenticating other endpoints
            - The response includes the user profile with its related customer and
              addresses (looked up by the authenticated user's id)

            The endpoint is protected by rate limiting to prevent brute force attacks.
            After multiple failed attempts, further login attempts will be temporarily blocked.

            Accepts both **application/x-www-form-urlencoded** (form data)
            and **application/json** body formats.
            """,
    responses={
        200: {"description": "Login successful, session created; returns user with customer and addresses"},
        401: {"description": "Authentication failed"},
        429: {"description": "Too many login attempts, try again later"},
    },
    response_description="CSRF token, access token, and the authenticated user with related customer and addresses",
    openapi_extra={
        "security": [],
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "User email or username"},
                            "password": {"type": "string", "description": "User password"}
                        },
                        "required": ["email", "password"]
                    }
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "User email or username"},
                            "password": {"type": "string", "description": "User password"}
                        },
                        "required": ["email", "password"]
                    }
                }
            }
        }
    }
)
async def login(
    request: Request,
    response: Response,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    """Login endpoint to get session cookies.

    Accepts both form-data (application/x-www-form-urlencoded) and JSON
    (application/json) request bodies.

    The session ID is set as an HTTP-only cookie. The CSRF token is set as a
    regular cookie and returned in the response. Credentials are verified by
    crudauth's hardened ``authenticate_password`` (timing-equalized check,
    disabled-account guard, escalating lockout that returns 429 + Retry-After).
    """
    # Parse credentials from request body (supports both JSON and form-data)
    content_type = request.headers.get("content-type", "").lower()

    email = ""
    password = ""

    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email", "")
            password = body.get("password", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON body",
            )
    else:
        try:
            form = await request.form()
            email = form.get("email", "")
            password = form.get("password", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Request body must be form-data or JSON with 'email' and 'password' fields",
            )

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'email' and 'password' are required",
        )

    logger.info("Login attempt", extra={"email": email})

    try:
        user = await crud_auth.authenticate_password(db, email, password, request=request)
    except HTTPException as exc:
        logger.warning("Login failed", extra={"email": email, "status": exc.status_code, "detail": exc.detail})
        raise
    except Exception as exc:
        logger.error("Login unexpected error", extra={"email": email, "error": str(exc)}, exc_info=True)
        raise

    email_verified = crud_auth.repo.get(user, "email_verified", False)
    logger.info("Login authenticate_password success", extra={"email": email, "email_verified": email_verified})

    if not email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    user_id = crud_auth.repo.user_id(user)
    session_id, csrf_token = await crud_auth.sessions.create_session(
        request,
        user_id=user_id,
        metadata={"login_type": "password", "username": crud_auth.repo.get(user, "username")},
    )
    crud_auth.sessions.set_session_cookies(response, session_id, csrf_token)

    token_body = _bearer_transport.issue_tokens(user, response=response)

    customer_result = await crud_customers.get_multi(
        db, schema_to_select=CustomerRead, user_id=user_id, deleted=False
    )
    customer = customer_result["data"][0] if customer_result.get("data") else None
    if customer:
        address_result = await crud_addresses.get_multi(
            db, schema_to_select=AddressRead, user_id=user_id, deleted=False
        )
        customer["addresses"] = address_result.get("data", []) if address_result else []

    return {
        "csrf_token": csrf_token,
        "access_token": token_body["access_token"],
        "token_type": token_body.get("token_type", "bearer"),
        "user": {
            "id": user_id,
            "email": crud_auth.repo.get(user, "email"),
            "name": crud_auth.repo.get(user, "name"),
            "username": crud_auth.repo.get(user, "username"),
            "customer": customer,
        },
    }


class FirebaseLoginRequest(BaseModel):
    firebase_token: str = Field(
        ...,
        description="Firebase ID Token (JWT) yang didapatkan setelah login dari client SDK Firebase.",
        examples=["eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMyJ9.eyJnZW1pbmkiOiJhbnRpZ3Jhdml0eSJ9..."]
    )

class FirebaseLoginResponse(BaseModel):
    csrf_token: str = Field(
        ...,
        description="CSRF Token untuk mengamankan request berikutnya.",
        examples=["a1b2c3d4e5f6g7h8..."]
    )
    access_token: str = Field(
        ...,
        description="Access token JWT untuk mengakses endpoint lainnya (berlaku 1 jam).",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    token_type: str = Field(
        default="bearer",
        description="Tipe token, selalu 'bearer'.",
        examples=["bearer"]
    )

@router.post(
    "/firebase-login",
    openapi_extra={"security": []},
    summary="Firebase Login",
    description="""
            Authenticates a user using a Firebase ID token.

            This endpoint accepts a Firebase ID token, verifies it against Google public
            certificates, and creates a local session for the user. The flow mirrors the
            Laravel implementation:
            - Decode the Firebase JWT header to get the key ID
            - Fetch Google public certificates (cached for 1 hour)
            - Verify the RSA-SHA256 signature
            - Validate standard claims (aud, iss, exp, iat)
            - Upsert user in the database and create a session
            """,
    response_model=FirebaseLoginResponse,
    responses={
        200: {
            "description": "Login successful, session created",
            "content": {
                "application/json": {
                    "example": {"csrf_token": "a1b2c3d4e5f6g7h8i9j0..."}
                }
            }
        },
        401: {
            "description": "Invalid or expired Firebase token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired Firebase token"}
                }
            }
        },
        422: {
            "description": "Missing firebase_token or invalid claims",
            "content": {
                "application/json": {
                    "example": {"detail": "Field firebase_token wajib diisi."}
                }
            }
        },
    },
    response_description="CSRF token for use in subsequent requests",
)
async def firebase_login(
    request: Request,
    db: AsyncSessionDep,
    response: Response,
    body: FirebaseLoginRequest,
) -> dict[str, str]:
    firebase_token = body.firebase_token

    verified_claims = verify_firebase_id_token(firebase_token)
    if verified_claims is None:
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase token")

    email = verified_claims.get("email")
    firebase_uid = verified_claims.get("sub")
    display_name = verified_claims.get("name")
    photo_url = verified_claims.get("picture")

    sign_in_provider = verified_claims.get("firebase", {}).get("sign_in_provider", "unknown")
    is_google_login = sign_in_provider == "google.com"
    auth_provider = "google" if is_google_login else sign_in_provider

    if not email or not firebase_uid:
        logger.warning("Firebase token missing email or uid", {"claims": verified_claims})
        raise HTTPException(status_code=422, detail="Firebase token does not contain required user info")

    user = await crud_users.get_multi(db=db, email=email, is_deleted=False)
    matched = None
    if user.get("data"):
        for u in user["data"]:
            if u.get("firebase_uid") == firebase_uid or u.get("email") == email:
                matched = u
                break

    if matched:
        update_data: dict[str, Any] = {
            "firebase_uid": firebase_uid,
            "oauth_provider": auth_provider,
            "email_verified": True,
        }
        if display_name:
            update_data["name"] = display_name
        if photo_url:
            update_data["profile_image_url"] = photo_url
        await crud_users.update(db=db, object=update_data, id=matched["id"])
        user_id = matched["id"]
        username = matched.get("username", "")
    else:
        import re
        
        base_username = re.sub(r"[^a-z0-9]", "", email.split("@")[0].lower())
        if len(base_username) < 2:
            base_username = base_username.ljust(2, "a")
            
        username = base_username[:20]
        counter = 1
        while await crud_users.exists(db=db, username=username):
            suffix = str(counter)
            username = base_username[:20 - len(suffix)] + suffix
            counter += 1

        name = (display_name or email)[:30]
        if len(name) < 2:
            name = name.ljust(2, "a")

        user_in = UserCreateInternal(
            name=name,
            username=username,
            email=email,
            hashed_password="",
            firebase_uid=firebase_uid,
            oauth_provider=auth_provider,
            email_verified=True,
            profile_image_url=photo_url or "https://www.profileimageurl.com",
        )
        created = await crud_users.create(db=db, object=user_in)
        user_id = created.get("id") if isinstance(created, dict) else getattr(created, "id")
        username = created.get("username", username) if isinstance(created, dict) else getattr(created, "username", username)
        
        from ...modules.customer.schemas import CustomerCreate
        customer_in = CustomerCreate(
            name=name[:100],
            email=email,
            user_id=user_id,
        )
        await crud_customers.create(db=db, object=customer_in)

    # Role assignment is disabled for firebase_login as per user request (RBAC is for user_admin)

    session_id, csrf_token = await crud_auth.sessions.create_session(
        request,
        user_id=user_id,
        metadata={
            "login_type": "firebase",
            "auth_provider": auth_provider,
            "firebase_uid": firebase_uid,
            "username": username,
        },
        expiration_seconds=3600,  # Firebase login session expires in 1 hour
    )
    crud_auth.sessions.set_session_cookies(response, session_id, csrf_token)

    from sqlalchemy import select
    from ...modules.user.models import User
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalar_one_or_none()
    token_body = _bearer_transport.issue_tokens(user, response=response)

    customer_result = await crud_customers.get_multi(
        db, schema_to_select=CustomerRead, user_id=user_id, deleted=False
    )
    customer = customer_result["data"][0] if customer_result.get("data") else None
    if customer:
        address_result = await crud_addresses.get_multi(
            db, schema_to_select=AddressRead, user_id=user_id, deleted=False
        )
        customer["addresses"] = address_result.get("data", []) if address_result else []

    return {
        "csrf_token": csrf_token,
        "access_token": token_body["access_token"],
        "token_type": token_body.get("token_type", "bearer"),
        "user": {
            "id": user_id,
            "email": email,
            "name": display_name or email,
            "username": username,
            "customer": customer,
        },
    }


@router.post(
    "/logout",
    summary="User Logout",
    description="""
            Terminates the current user session.

            This endpoint:
            - Invalidates the active session in the storage backend
            - Clears all session-related cookies from the client

            After logout, the user will need to authenticate again to access
            protected resources. Any existing session tokens will no longer be valid.
            """,
    responses={200: {"description": "Logout successful, session terminated"}, 401: {"description": "Not authenticated"}},
    response_description="Confirmation of successful logout",
)
async def logout(
    response: Response,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> dict[str, str]:
    """Logout endpoint to terminate the session and clear cookies (CSRF-protected)."""
    session_id = principal.metadata.get("session_id")
    if session_id:
        await crud_auth.sessions.revoke(session_id, owner_id=principal.user_id)
    crud_auth.sessions.clear_session_cookies(response)

    return {"message": "Logged out successfully"}


@router.post(
    "/refresh-csrf",
    summary="Refresh CSRF Token",
    description="""
            Generates a new CSRF token for the current session.

            This endpoint should be called to obtain a fresh CSRF token when:
            - The current token is about to expire
            - After a certain period of inactivity
            - When increased security is needed for sensitive operations

            The new token is returned in the response and also set as a cookie.
            """,
    responses={200: {"description": "New CSRF token generated successfully"}, 401: {"description": "Not authenticated"}},
    response_description="The new CSRF token for the session",
)
async def refresh_csrf_token(
    request: Request,
    response: Response,
) -> dict[str, str]:
    """Generate a new CSRF token for the current session.

    Deliberately resolves the session cookie directly rather than via
    ``current_user`` - requiring a valid CSRF header to refresh CSRF would defeat
    the recovery purpose. The session cookie is httpOnly and the new token only
    lands in the (same-origin-readable) cookie + body.
    """
    sessions = crud_auth.sessions
    session_id = request.cookies.get(sessions.session_cookie_name)
    session = await sessions.validate_session(session_id) if session_id else None
    if session is None or session_id is None:
        raise UnauthorizedException("Not authenticated")

    ttl_seconds = sessions.timeout_seconds_for(session.metadata)
    csrf_token = await sessions.regenerate_csrf_token(
        user_id=session.user_id, session_id=session_id, expiration_seconds=ttl_seconds
    )
    sessions.set_csrf_cookie(response, csrf_token, max_age=ttl_seconds)

    return {"csrf_token": csrf_token}


@router.get(
    "/oauth/google",
    openapi_extra={"security": []},
    summary="Initiate Google OAuth Login",
    description="""
            Starts the OAuth 2.0 authentication flow with Google.

            This endpoint generates the authorization URL that the user should be
            redirected to in order to authenticate with Google. The flow includes:
            - Creation of a state parameter for CSRF protection
            - Generation of PKCE code challenge (for enhanced security)
            - Setting appropriate OAuth scopes for profile access

            After successful authentication with Google, the user will be redirected
            back to this application's callback endpoint.

            An optional redirect_uri can be specified to control where the user
            is sent after the entire authentication process completes.
            """,
    responses={
        200: {"description": "Authorization URL generated successfully"},
        500: {"description": "Failed to initiate Google login"},
    },
    response_description="The Google authorization URL to redirect the user to",
)
async def oauth_google_login(
    request: Request,
    redirect_uri: str | None = Query(None),
) -> dict[str, str]:
    """Initiate the Google OAuth flow: build the authorization URL and stash state + PKCE."""
    try:
        auth_data = oauth_providers["google"].get_authorization_url()
        state_obj = OAuthState(
            state=auth_data["state"],
            provider=OAuthProvider.GOOGLE.value,
            redirect_to=redirect_uri,
            code_verifier=auth_data.get("code_verifier"),
        )
        await oauth_state_storage.create(state_obj, session_id=auth_data["state"], expiration=OAUTH_STATE_TTL_SECONDS)
        return {"url": auth_data["url"]}
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate Google login")


@router.get(
    "/oauth/callback/google",
    openapi_extra={"security": []},
    summary="Google OAuth Callback Handler",
    description="""
            Processes the authentication callback from Google OAuth.

            This endpoint handles the authorization code returned by Google after
            the user has successfully authenticated. The process includes:
            - Validating the state parameter to prevent CSRF attacks
            - Exchanging the authorization code for access/refresh tokens
            - Fetching the user profile from Google
            - Creating or updating the user account in the system
            - Establishing a new session for the authenticated user

            Two response formats are supported:
            - redirect: Redirects to the frontend with success/error parameters (default)
            - json: Returns user information and tokens as a JSON response

            The json format is useful for mobile apps or single-page applications that
            handle the OAuth flow programmatically.
            """,
    responses={
        200: {"description": "Authentication successful (JSON response)"},
        302: {"description": "Authentication successful (redirect response)"},
        400: {"description": "Invalid OAuth state or other parameter"},
        401: {"description": "Authentication failed"},
        500: {"description": "Server error during authentication"},
    },
    response_description="Authentication result with session cookies set",
)
async def oauth_google_callback(
    request: Request,
    response: Response,
    db: AsyncSessionDep,
    code: str = Query(...),
    state: str = Query(...),
    response_format: str = Query("redirect", description="Response format, either 'redirect' or 'json'"),
):
    """Handle the Google OAuth callback: verify state, link/create the user, start a session."""
    state_data = await oauth_state_storage.get(state, OAuthState)

    if not state_data:
        logger.warning(f"Invalid OAuth state in callback: {state}")
        if response_format == "json":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
        return RedirectResponse(
            url=f"/login?error=oauth_error&provider={OAuthProvider.GOOGLE.value}&reason=invalid_state",
            status_code=status.HTTP_302_FOUND,
        )

    if state_data.provider != OAuthProvider.GOOGLE.value:
        logger.warning(f"Provider mismatch in OAuth callback: expected google, got {state_data.provider}")
        if response_format == "json":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider mismatch")
        return RedirectResponse(
            url=f"/login?error=oauth_error&provider={OAuthProvider.GOOGLE.value}&reason=provider_mismatch",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        provider = oauth_providers["google"]
        token_data = await provider.exchange_code(code, code_verifier=state_data.code_verifier)
        user_info_raw = await provider.get_user_info(token_data["access_token"])
        user_info = await provider.process_user_info(user_info_raw)

        user, is_new_user = await oauth_account_service.get_or_create_user(user_info, db)
        user_id = crud_auth.repo.user_id(user)
        username = crud_auth.repo.get(user, "username")

        session_id, csrf_token = await crud_auth.sessions.create_session(
            request,
            user_id=user_id,
            metadata={
                "login_type": "oauth",
                "oauth_provider": OAuthProvider.GOOGLE.value,
                "username": username,
                "is_new_user": is_new_user,
            },
        )
        crud_auth.sessions.set_session_cookies(response, session_id, csrf_token)

        await oauth_state_storage.delete(state)

        if response_format == "json":
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": crud_auth.repo.get(user, "email"),
                    "is_new_user": is_new_user,
                },
                "csrf_token": csrf_token,
            }

        redirect_to = str(state_data.redirect_to) if state_data.redirect_to else "/"
        return RedirectResponse(url=redirect_to, status_code=status.HTTP_302_FOUND)

    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {str(e)}", exc_info=True)

        if response_format == "json":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OAuth authentication failed: {str(e)}"
            )

        return RedirectResponse(
            url=f"/login?error=oauth_error&provider={OAuthProvider.GOOGLE.value}",
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/check-auth", openapi_extra={"security": []})
async def check_auth(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
    db: AsyncSessionDep,
) -> dict[str, Any]:
    """
    Check if the user is authenticated and return basic user information.

    This is useful for clients to verify authentication status. It responds to both
    authenticated and anonymous callers (anonymous gets ``authenticated: false``
    rather than a 401).

    Returns:
        Authentication status and user information if authenticated.
    """
    if principal is None:
        return {"authenticated": False, "message": "Not authenticated"}

    try:
        user = await crud_users.get(db=db, id=principal.user_id, is_deleted=False)

        if not user:
            return {"authenticated": False, "message": "User not found"}

        session_id = principal.metadata.get("session_id")
        session = await crud_auth.sessions.validate_session(session_id) if session_id else None

        return {
            "authenticated": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "oauth_provider": user.get("oauth_provider"),
            },
            "session": {
                "created_at": session.created_at.isoformat() if session and session.created_at else None,
                "last_activity": session.last_activity.isoformat() if session and session.last_activity else None,
            },
        }
    except Exception as e:
        logger.error(f"Error checking authentication: {str(e)}", exc_info=True)
        return {"authenticated": False, "message": "Error checking authentication status"}
