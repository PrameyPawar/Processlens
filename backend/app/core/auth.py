"""
Core cryptographic authentication utilities for ProcessLens.
Provides password hashing via scrypt (OWASP-recommended) and
cryptographically signed session tokens via HMAC-SHA256 URLSafeTimedSerializer.
"""

from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.core.config import settings

import uuid
import time

# Salt for token serialization to prevent cross-purpose key reuse
AUTH_TOKEN_SALT = "processlens-auth-v1"

def hash_password(password: str) -> str:
    """
    Hash a password using scrypt (memory-hard, resistant to hardware brute-force).
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    return generate_password_hash(password, method="scrypt")

def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored scrypt hash in constant time.
    """
    if not password or not password_hash:
        return False
    return check_password_hash(password_hash, password)

def create_auth_token(payload: Dict[str, Any]) -> str:
    """
    Serialize and cryptographically sign an authentication payload with HMAC-SHA256 timestamp.
    Embeds unique token ID (jti) and issued-at (iat) timestamp for server-side revocation tracking.
    """
    token_payload = dict(payload)
    if "jti" not in token_payload:
        token_payload["jti"] = f"tok_{uuid.uuid4().hex}"
    if "iat" not in token_payload:
        token_payload["iat"] = time.time()
    serializer = URLSafeTimedSerializer(settings.AUTH_SECRET_KEY, salt=AUTH_TOKEN_SALT)
    return serializer.dumps(token_payload)

def decode_auth_token(token: str, max_age: Optional[int] = None) -> Dict[str, Any]:
    """
    Verify signature and decode an authentication token.
    Raises ValueError on expired or tampered tokens.
    """
    if max_age is None:
        max_age = settings.AUTH_TOKEN_EXPIRE_SECONDS
    
    serializer = URLSafeTimedSerializer(settings.AUTH_SECRET_KEY, salt=AUTH_TOKEN_SALT)
    try:
        data = serializer.loads(token, max_age=max_age)
        if not isinstance(data, dict):
            raise ValueError("Invalid token payload structure.")
        return data
    except SignatureExpired:
        raise ValueError("Session token has expired. Please log in again.")
    except BadSignature:
        raise ValueError("Invalid or tampered session token.")
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")

def extract_token_jti(token: str) -> Optional[str]:
    """
    Extract the jti (token ID) from a signed token for revocation purposes.
    Works even if max_age has elapsed, as long as signature is authentic.
    """
    try:
        serializer = URLSafeTimedSerializer(settings.AUTH_SECRET_KEY, salt=AUTH_TOKEN_SALT)
        success, payload = serializer.loads_unsafe(token)
        if success and isinstance(payload, dict):
            return payload.get("jti")
    except Exception:
        pass
    return None


