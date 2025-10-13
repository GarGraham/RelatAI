"""Audit trail retrieval endpoints."""

from fastapi import APIRouter, HTTPException, status

from relat_ai.core.models import AuditLogModel
from relat_ai.services.audit_trail import get_audit_log, list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", summary="List audit logs for all datasets", response_model=list[AuditLogModel])
async def list_logs() -> list[AuditLogModel]:
    """Return audit logs for all datasets."""

    return [log.to_model() for log in list_audit_logs()]


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

