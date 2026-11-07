"""
Customer workspace and tenant-scoped operations API endpoints.
Protected: Strictly restricted to authenticated users with the 'customer' role.
Developers and unauthenticated clients receive 403 Forbidden or 401 Unauthorized.
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.dependencies import require_customer_only
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/customer", tags=["Customer Workspace"])

class CustomerWorkspaceResponse(BaseModel):
    workspace_id: str = Field(..., description="Stable identifier derived from the authenticated user; no workspace data is persisted")
    owner_id: str = Field(..., description="Authenticated customer user ID")
    owner_email: str = Field(..., description="Authenticated customer email")
    workspace_name: str = Field(..., description="Display name derived from the authenticated user")
    status: str = Field(default="ready", description="Identity response status, not persistent workspace readiness")
    isolation_tier: str = Field(default="identity-only", description="No persisted customer datasets or workspace objects are implemented")

@router.get("/workspace", response_model=CustomerWorkspaceResponse, status_code=status.HTTP_200_OK)
def get_customer_workspace(customer_user: UserResponse = Depends(require_customer_only)):
    """
    Return identity-derived workspace metadata for the authenticated customer.
    No customer datasets or persistent workspace objects are stored by this endpoint.
    """
    return CustomerWorkspaceResponse(
        workspace_id=f"ws_{customer_user.id}",
        owner_id=customer_user.id,
        owner_email=customer_user.email,
        workspace_name=f"{customer_user.name}'s Operations Workspace",
        status="ready",
        isolation_tier="identity-only",
    )
