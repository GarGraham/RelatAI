"""Dataset upload and profiling API routes."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from relat_ai.core.models import DatasetUploadResponse
from relat_ai.services.ingestion import get_dataset, save_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])

DatasetUpload = Annotated[UploadFile, File(...)]


@router.post(
    "/upload",
    summary="Upload a dataset and return profiling metadata",
    status_code=status.HTTP_201_CREATED,
    response_model=DatasetUploadResponse,
)
async def upload_dataset(file: DatasetUpload) -> DatasetUploadResponse:
    """Persist an uploaded dataset and return the schema profile."""

    try:
        return save_upload(file.file, file.filename or "dataset", content_type=file.content_type)
    except ValueError as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/{dataset_id}",
    summary="Retrieve a previously uploaded dataset profile",
    response_model=DatasetUploadResponse,
)
async def retrieve_dataset(dataset_id: str) -> DatasetUploadResponse:
    """Return metadata and schema profile for a stored dataset."""

    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset
