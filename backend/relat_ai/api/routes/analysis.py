"""API routes exposing analysis execution capabilities."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from relat_ai.core.results import AnalysisResultResponse, AnalysisRunRequest
from relat_ai.services.analysis_runner import (
    AnalysisExecutionError,
    DatasetNotFoundError,
    execute_analysis,
)


router = APIRouter(prefix="/datasets", tags=["analysis"])


@router.post(
    "/{dataset_id}/analyze",
    response_model=AnalysisResultResponse,
    summary="Execute analysis on configured dataset",
)
async def analyze_dataset(
    dataset_id: str, request: AnalysisRunRequest | None = None
) -> AnalysisResultResponse:
    """Execute the configured analysis for ``dataset_id`` and return results."""

    try:
        return execute_analysis(dataset_id, request)
    except DatasetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (AnalysisExecutionError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValidationError as exc:
        detail = {
            "detail": exc.errors(),
            "message": "Request validation failed",
        }
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc

