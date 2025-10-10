"""Health check endpoint for uptime monitoring."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["system"])


@router.get("", summary="Service heartbeat")
async def healthcheck() -> dict[str, str]:
    """Return a simple heartbeat payload indicating the API is healthy."""
    return {"status": "ok"}
