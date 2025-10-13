"""Audit trail retrieval endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from relat_ai.core.models import AuditLogModel
from relat_ai.services.audit_trail import get_audit_log, list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", summary="List audit logs for all datasets", response_model=list[AuditLogModel])
async def list_logs(
    skip: Annotated[int, Query(ge=0, description="Number of logs to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of logs to return")] = 50,
) -> list[AuditLogModel]:
    """Return audit logs for all datasets with pagination support.
    
    Args:
        skip: Number of logs to skip (for pagination). Default is 0.
        limit: Maximum number of logs to return (1-100). Default is 50.
    
    Returns:
        List of audit logs sorted by creation time (newest first).
    """

    all_logs = list_audit_logs()
    # Sort by created_at descending (newest first)
    sorted_logs = sorted(all_logs, key=lambda log: log.created_at, reverse=True)
    # Apply pagination
    paginated_logs = sorted_logs[skip : skip + limit]
    return [log.to_model() for log in paginated_logs]


@router.get(
    "/{dataset_id}",
    summary="Retrieve the audit log for a dataset",
    response_model=AuditLogModel,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Audit log not found"}},
)
async def retrieve_log(dataset_id: str) -> AuditLogModel:
    """Return the audit log for a specific dataset."""

    log = get_audit_log(dataset_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
    return log.to_model()

