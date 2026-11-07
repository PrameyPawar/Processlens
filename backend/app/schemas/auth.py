"""
Pydantic schemas for authentication and authorization.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserRole:
    CUSTOMER = "customer"
    DEVELOPER = "developer"
    ALL = [CUSTOMER, DEVELOPER]

class UserBase(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="Full user name")
    role: str = Field(default=UserRole.CUSTOMER, description="User role ('customer' or 'developer')")

class UserCreate(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=2, max_length=100, description="Full user name")
    password: str = Field(..., min_length=12, description="Password (at least 12 characters)")

class UserResponse(BaseModel):
    id: str = Field(..., description="Unique user ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="Full user name")
    role: str = Field(..., description="Assigned role")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="Signed authentication token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in_seconds: int = Field(..., description="Token lifespan in seconds")
    user: UserResponse = Field(..., description="Authenticated user profile")

class PasswordResetRequest(BaseModel):
    email: str = Field(..., description="User email address")

class PasswordResetResponse(BaseModel):
    message: str = Field(..., description="Status message")

class DevStatusResponse(BaseModel):
    status: str = Field(default="ok", description="Overall system status")
    version: str = Field(..., description="ProcessLens application version")
    environment: str = Field(..., description="Running environment (development / production)")
    python_version: str = Field(..., description="Python runtime version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    cors_origins_configured: int = Field(..., description="Number of configured CORS origins")
    llm_provider_configured: bool = Field(..., description="Whether external LLM is configured")
    max_file_size_mb: int = Field(..., description="Ingestion file size limit in MB")

class AuditEvent(BaseModel):
    id: str = Field(..., description="Event ID")
    timestamp: str = Field(..., description="ISO timestamp")
    event_type: str = Field(..., description="Event type (e.g. LOGIN_SUCCESS, LOGIN_FAILED, RATE_LIMITED)")
    email_masked: str = Field(..., description="Masked email for privacy")
    client_ip: str = Field(..., description="Client IP address")
    details: Optional[str] = Field(None, description="Non-sensitive operational details")

class DevAuditEventsResponse(BaseModel):
    events: List[AuditEvent] = Field(default_factory=list, description="Recent operational security events")
