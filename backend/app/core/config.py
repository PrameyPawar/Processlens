"""
Application settings and constants for ProcessLens.
"""

import os
import secrets
from typing import List, Optional
from urllib.parse import urlparse

class Settings:
    PROJECT_NAME: str = "ProcessLens API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Ingestion constraints
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: List[str] = [".csv"]
    ALLOWED_MIME_TYPES: List[str] = [
        "text/csv",
        "application/vnd.ms-excel",
        "text/csv; charset=utf-8",
        "text/plain",
        "application/octet-stream"
    ]
    
    # Canonical event log schema standards
    CANONICAL_REQUIRED_COLUMNS: List[str] = ["case_id", "activity", "timestamp"]

    # LLM Provider Configuration
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY", None)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://testserver"
        ).split(",")
        if origin.strip()
    ]

    # Authentication & Session Security
    DEFAULT_DEV_SECRET: str = "processlens-secure-dev-session-key-change-in-production-2026"
    AUTH_SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY") or secrets.token_urlsafe(48)
    AUTH_SECRET_KEY_CONFIGURED: bool = bool(os.getenv("AUTH_SECRET_KEY"))
    AUTH_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("AUTH_TOKEN_EXPIRE_SECONDS", "28800"))  # 8 hours
    AUTH_COOKIE_NAME: str = "processlens_session"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    TRUSTED_PROXY_IPS: List[str] = [
        ip.strip() for ip in os.getenv("TRUSTED_PROXY_IPS", "").split(",") if ip.strip()
    ]

    # In production, secure cookies are mandatory unless explicitly turned off for testing
    AUTH_SECURE_COOKIE: bool = (
        os.getenv("AUTH_SECURE_COOKIE", "true" if os.getenv("ENVIRONMENT", "").lower() in {"staging", "production"} else "false").lower() in ("true", "1")
    )

    # Durable Storage Configuration (Optional SQLite path for persistence across restarts)
    USER_STORE_DB_PATH: Optional[str] = os.getenv("USER_STORE_DB_PATH", None)

    # Password Recovery Delivery Configuration
    EMAIL_DELIVERY_ENABLED: bool = os.getenv("EMAIL_DELIVERY_ENABLED", "false").lower() in ("true", "1")
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST", None)
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", None)

    # Seed account passwords are generated per process unless supplied via environment variables.
    DEV_ADMIN_EMAIL: str = os.getenv("DEV_ADMIN_EMAIL", "dev@processlens.internal")
    DEV_ADMIN_PASSWORD: str = os.getenv("DEV_ADMIN_PASSWORD") or secrets.token_urlsafe(24)
    DEV_ADMIN_PASSWORD_CONFIGURED: bool = bool(os.getenv("DEV_ADMIN_PASSWORD"))
    DEMO_CUSTOMER_EMAIL: str = os.getenv("DEMO_CUSTOMER_EMAIL", "customer@processlens.com")
    DEMO_CUSTOMER_PASSWORD: str = os.getenv("DEMO_CUSTOMER_PASSWORD") or secrets.token_urlsafe(24)
    DEMO_CUSTOMER_PASSWORD_CONFIGURED: bool = bool(os.getenv("DEMO_CUSTOMER_PASSWORD"))

    def validate_configuration(self) -> None:
        """Reject unknown environments and unsafe production-like settings at startup."""
        allowed_environments = {"development", "test", "staging", "production"}
        if self.ENVIRONMENT not in allowed_environments:
            raise ValueError("ENVIRONMENT must be one of: development, test, staging, production.")

        if self.ENVIRONMENT in {"staging", "production"}:
            errors: List[str] = []
            if not self.AUTH_SECRET_KEY_CONFIGURED:
                errors.append("AUTH_SECRET_KEY must be explicitly configured in production-like environments.")
            if self.AUTH_SECRET_KEY == self.DEFAULT_DEV_SECRET:
                errors.append("AUTH_SECRET_KEY must be changed from the development default in production-like environments.")
            if len(self.AUTH_SECRET_KEY) < 32:
                errors.append("AUTH_SECRET_KEY must be at least 32 characters long in production-like environments.")
            if not self.AUTH_SECURE_COOKIE:
                errors.append("AUTH_SECURE_COOKIE must be enabled (true) in production-like environments behind HTTPS.")
            if not self.DEV_ADMIN_PASSWORD_CONFIGURED:
                errors.append("DEV_ADMIN_PASSWORD must be explicitly configured in production-like environments.")
            if not self.DEMO_CUSTOMER_PASSWORD_CONFIGURED:
                errors.append("DEMO_CUSTOMER_PASSWORD must be explicitly configured in production-like environments.")
            if not self.USER_STORE_DB_PATH:
                errors.append("USER_STORE_DB_PATH must point to durable shared storage in production-like environments.")
            if len(self.DEV_ADMIN_PASSWORD) < 12:
                errors.append("DEV_ADMIN_PASSWORD must be at least 12 characters in production-like environments.")
            if len(self.DEMO_CUSTOMER_PASSWORD) < 12:
                errors.append("DEMO_CUSTOMER_PASSWORD must be at least 12 characters in production-like environments.")
            if self.DEV_ADMIN_PASSWORD == self.DEMO_CUSTOMER_PASSWORD:
                errors.append("Seed account passwords must be different in production-like environments.")
            if "*" in self.CORS_ORIGINS:
                errors.append("CORS_ORIGINS cannot contain wildcard '*' when serving authenticated production users.")
            if any(urlparse(origin).scheme != "https" or not urlparse(origin).netloc for origin in self.CORS_ORIGINS):
                errors.append("CORS_ORIGINS must contain only valid HTTPS origins in production-like environments.")
            if errors:
                raise ValueError("Production-like configuration validation failed:\n - " + "\n - ".join(errors))

settings = Settings()
