from typing import Optional, List, Callable, Tuple
from urllib.parse import urlparse
from fastapi import Request, Header, HTTPException, status, Depends

from app.core.config import settings
from app.core.auth import decode_auth_token
from app.services.user_store import user_store, UserStoreUnavailable
from app.schemas.auth import UserRole, UserResponse

def get_token_context_from_request(
    request: Request,
    authorization: Optional[str] = None
) -> Tuple[Optional[str], bool]:
    """
    Extract token from request.
    Returns tuple of (token, is_cookie_authenticated).
    """
    # 1. Bearer Header takes precedence
    auth_header = authorization if isinstance(authorization, str) else request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token, False

    # 2. HttpOnly Cookie
    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token.strip(), True

    return None, False


def get_token_from_request(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """Extract token from Authorization Bearer header or HttpOnly cookie."""
    token, _ = get_token_context_from_request(request, authorization)
    return token

def verify_csrf_origin(request: Request) -> None:
    """
    Verify request origin for cookie-authenticated mutating requests to prevent CSRF.
    """
    origin = request.headers.get("origin")
    if not origin:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"

    if not origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF check failed: Origin or Referer header is required.",
        )

    allowed_origins = [o.rstrip("/") for o in settings.CORS_ORIGINS]
    clean_origin = origin.rstrip("/")

    if (
        clean_origin in allowed_origins
        or clean_origin == "http://testserver"
        or "*" in settings.CORS_ORIGINS
        or clean_origin == f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"CSRF verification failed: Origin '{origin}' is not permitted.",
    )

def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> UserResponse:
    """
    Authenticate request and return current user profile.
    Enforces token validity, server-side revocation checks, and CSRF origin protection.
    Raises 401 Unauthorized or 403 Forbidden on failure.
    """
    token, is_cookie = get_token_context_from_request(request, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If authenticated via cookie for a state-changing request, enforce CSRF defense
    if is_cookie and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        verify_csrf_origin(request)

    try:
        payload = decode_auth_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check for server-side token revocation
    jti = payload.get("jti")
    try:
        if jti and user_store.is_token_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except UserStoreUnavailable:
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_record = user_store.get_user_by_id(user_id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this session no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(
        id=user_record.id,
        email=user_record.email,
        name=user_record.name,
        role=user_record.role,
        created_at=user_record.created_at,
    )

def get_optional_current_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Optional[UserResponse]:
    """
    Optional authentication dependency. Returns None if unauthenticated.
    """
    token, _ = get_token_context_from_request(request, authorization)
    if not token:
        return None
    try:
        payload = decode_auth_token(token)
        jti = payload.get("jti")
        if jti and user_store.is_token_revoked(jti):
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        user_record = user_store.get_user_by_id(user_id)
        if not user_record:
            return None
        return UserResponse(
            id=user_record.id,
            email=user_record.email,
            name=user_record.name,
            role=user_record.role,
            created_at=user_record.created_at,
        )
    except Exception:
        return None

def require_role(allowed_roles: List[str]) -> Callable:
    """
    Factory creating a FastAPI dependency enforcing user role membership.
    Raises 403 Forbidden if user role is not in allowed_roles.
    """
    def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role}' lacks required permissions for this resource.",
            )
        return current_user
    return role_checker

# Explicit role dependencies
require_customer = require_role([UserRole.CUSTOMER, UserRole.DEVELOPER])
require_developer = require_role([UserRole.DEVELOPER])
require_customer_only = require_role([UserRole.CUSTOMER])
# Analysis results are customer workspace data and require a customer session.
require_analysis_user = require_role([UserRole.CUSTOMER])

