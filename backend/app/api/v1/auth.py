"""
Authentication API endpoints for customer and developer sign-in,
registration, profile retrieval, logout, and password reset.
"""

from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from ipaddress import ip_address
from app.core.config import settings
from app.core.auth import create_auth_token, verify_password, extract_token_jti
from app.core.dependencies import (
    get_current_user,
    get_token_from_request,
    get_token_context_from_request,
    verify_csrf_origin,
)
from app.services.user_store import user_store, UserStoreUnavailable

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
    PasswordResetRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_client_ip(request: Request) -> str:
    """Trust forwarded client addresses only when the direct peer is explicitly trusted."""
    peer_ip = request.client.host if request.client else "unknown"
    if peer_ip not in settings.TRUSTED_PROXY_IPS:
        return peer_ip

    forwarded = request.headers.get("X-Forwarded-For", "")
    if not forwarded:
        return peer_ip

    # A trusted edge proxy using X-Forwarded-For appends the address it observed.
    candidate = forwarded.split(",")[-1].strip()
    try:
        return str(ip_address(candidate))
    except ValueError:
        return peer_ip

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(request: Request, response: Response, credentials: LoginRequest):
    """
    Authenticate user credentials (customer or developer).
    Enforces rate limiting to prevent brute-force attacks and returns generic error messages.
    Sets a secure HttpOnly session cookie and returns an access token.
    """
    client_ip = get_client_ip(request)
    email = credentials.email.strip().lower()

    # 1. Check Rate Limiter
    if not user_store.consume_rate_limit(client_ip) or not user_store.consume_rate_limit(email):
        user_store.record_audit_event("RATE_LIMITED", email, client_ip, "Exceeded maximum failed login attempts")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 5 minutes before trying again.",
        )

    # 2. Lookup User
    user = user_store.get_user_by_email(email)
    if not user or not verify_password(credentials.password, user.password_hash):
        user_store.record_audit_event("LOGIN_FAILED", email, client_ip, "Invalid credentials")
        # Generic error message: never reveal whether email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Successful Authentication
    user_store.reset_attempts(client_ip)
    user_store.reset_attempts(email)
    user_store.record_audit_event("LOGIN_SUCCESS", user.email, client_ip, f"Role: {user.role}")

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
    }
    token = create_auth_token(token_payload)

    # 4. Set HttpOnly Session Cookie
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.AUTH_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=settings.AUTH_SECURE_COOKIE,
        samesite="lax",
        path="/",
    )

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.AUTH_TOKEN_EXPIRE_SECONDS,
        user=user_response,
    )

@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, response: Response, user_in: UserCreate):
    """
    Public registration endpoint.
    Strictly assigns the 'customer' role on the server.
    Developer roles can never be registered via this endpoint.
    """
    client_ip = get_client_ip(request)
    registration_key = f"registration_{client_ip}"
    if not user_store.consume_rate_limit(registration_key, max_attempts=5, window_seconds=3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )
    try:
        new_user = user_store.create_customer_user(
            email=user_in.email,
            name=user_in.name,
            password=user_in.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    user_store.record_audit_event("USER_REGISTERED", new_user.email, client_ip, "Customer account created")

    token_payload = {
        "sub": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "name": new_user.name,
    }
    token = create_auth_token(token_payload)

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.AUTH_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=settings.AUTH_SECURE_COOKIE,
        samesite="lax",
        path="/",
    )

    user_response = UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        created_at=new_user.created_at,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.AUTH_TOKEN_EXPIRE_SECONDS,
        user=user_response,
    )

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_profile(current_user: UserResponse = Depends(get_current_user)):
    """
    Return currently authenticated user profile.
    Requires valid cookie or Bearer token.
    """
    return current_user

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: Request, response: Response):
    """
    Clear session cookie and invalidate server-side session token.
    Enforces CSRF origin verification on cookie-authenticated requests.
    """
    token, is_cookie = get_token_context_from_request(request)
    if is_cookie:
        verify_csrf_origin(request)

    if token:
        jti = extract_token_jti(token)
        if jti:
            try:
                user_store.revoke_token(jti)
            except UserStoreUnavailable:
                raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable.")

    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        samesite="lax",
        httponly=True,
        secure=settings.AUTH_SECURE_COOKIE,
    )
    return {"message": "Logged out successfully."}


@router.post("/forgot-password", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def forgot_password(request: Request, body: PasswordResetRequest):
    """
    Handle password reset requests.
    If email delivery is not configured, honestly indicates that automated password recovery
    is not enabled in this deployment rather than simulating delivery.
    """
    client_ip = get_client_ip(request)
    email = body.email.strip().lower()

    if not user_store.consume_rate_limit(f"reset_{client_ip}", max_attempts=3, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please wait 10 minutes before retrying.",
        )

    # SMTP settings alone do not implement token generation, delivery, or safe
    # password replacement. Never claim a reset email was sent until that flow exists.
    user_store.record_audit_event(
        "PASSWORD_RESET_UNAVAILABLE",
        email,
        client_ip,
        "Password recovery flow is not implemented",
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password recovery is not implemented in this build. Please contact your system administrator.",
    )

