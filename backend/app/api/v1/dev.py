"""
Developer diagnostics and operational status API endpoints.
Strictly restricted to users authenticated with the 'developer' role.
"""

import sys
import time
from fastapi import APIRouter, Depends
from app.core.config import settings
from app.core.dependencies import require_developer
from app.services.user_store import user_store
from app.schemas.auth import DevStatusResponse, DevAuditEventsResponse

router = APIRouter(prefix="/dev", tags=["Developer Diagnostics"])

# Record server start time for uptime calculation
SERVER_START_TIME = time.time()

@router.get("/status", response_model=DevStatusResponse)
def get_developer_status(dev_user=Depends(require_developer)):
    """
    Retrieve system diagnostic and operational status.
    Protected: Only authenticated developers can access this endpoint.
    Customers receive 403 Forbidden.
    """
    uptime = time.time() - SERVER_START_TIME
    return DevStatusResponse(
        status="ok",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        python_version=sys.version.split()[0],
        uptime_seconds=round(uptime, 1),
        cors_origins_configured=len(settings.CORS_ORIGINS),
        llm_provider_configured=bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip()),
        max_file_size_mb=settings.MAX_FILE_SIZE_BYTES // (1024 * 1024),
    )

@router.get("/audit-events", response_model=DevAuditEventsResponse)
def get_audit_events(dev_user=Depends(require_developer)):
    """
    Retrieve recent non-sensitive security and operational audit events.
    Protected: Only authenticated developers can access this endpoint.
    Emails are masked and no secrets/passwords are ever logged or exposed.
    """
    events = user_store.get_recent_audit_events(limit=50)
    return DevAuditEventsResponse(events=events)
