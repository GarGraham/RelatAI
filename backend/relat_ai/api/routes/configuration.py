"""API endpoints for dataset configuration management and filtering."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from relat_ai.core.models import (
    ConfigurationPreviewResponse,
    ConfigurationTemplate,
    ConfigurationTemplateCreate,
    ConfigurationUpdateRequest,
    DatasetConfiguration,
)
from relat_ai.services.configuration import (
    apply_configuration_to_frame,
    get_configuration,
    initialise_configuration,
    normalise_configuration,
    replace_configuration,
    update_configuration,
)
from relat_ai.services.ingestion import get_registry, load_frame
from relat_ai.services.templates import create_template, delete_template, get_template, list_templates

router = APIRouter(prefix="/datasets", tags=["configuration"])

PreviewLimit = Annotated[int, Query(ge=1, le=500, description="Maximum rows returned in the preview")]


def _get_dataset_record(dataset_id: str):
    record = get_registry().get(dataset_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return record


@router.get(
    "/{dataset_id}/configuration",
    response_model=DatasetConfiguration,
    summary="Retrieve the configuration for a dataset",
)
async def read_configuration(dataset_id: str) -> DatasetConfiguration:
    record = _get_dataset_record(dataset_id)
    configuration = get_configuration(dataset_id)
    if configuration is None:
        configuration = initialise_configuration(dataset_id, record.profile)
    return configuration


@router.patch(
    "/{dataset_id}/configuration",
    response_model=DatasetConfiguration,
    summary="Update configuration options for a dataset",
    description=(
        "Filters support partial updates: ``null`` leaves existing filters in place, ``{}`` clears all "
        "filters, and providing column mappings replaces those specific filters."
    ),
)
async def patch_configuration(
    dataset_id: str, payload: ConfigurationUpdateRequest
) -> DatasetConfiguration:
    record = _get_dataset_record(dataset_id)
    try:
        return update_configuration(dataset_id, payload, record.profile)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get(
    "/{dataset_id}/configuration/preview",
    response_model=ConfigurationPreviewResponse,
    summary="Preview the dataset after applying configuration filters",
)
async def preview_configuration(dataset_id: str, limit: PreviewLimit = 50) -> ConfigurationPreviewResponse:
    record = _get_dataset_record(dataset_id)
    configuration = get_configuration(dataset_id)
    if configuration is None:
        configuration = initialise_configuration(dataset_id, record.profile)

    frame = load_frame(record.metadata.path)
    filtered = apply_configuration_to_frame(frame, configuration)
    preview_frame = filtered.head(limit)
    return ConfigurationPreviewResponse(
        dataset_id=dataset_id,
        row_count=int(filtered.shape[0]),
        columns=list(preview_frame.columns),
        preview=preview_frame.to_dict(orient="records"),
    )


@router.post(
    "/{dataset_id}/templates",
    response_model=ConfigurationTemplate,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reusable configuration template",
)
async def create_configuration_template(
    dataset_id: str,
    payload: ConfigurationTemplateCreate,
) -> ConfigurationTemplate:
    record = _get_dataset_record(dataset_id)
    if payload.configuration is not None:
        try:
            configuration = normalise_configuration(dataset_id, payload.configuration, record.profile)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    else:
        configuration = initialise_configuration(dataset_id, record.profile)
    return create_template(
        dataset_id=dataset_id,
        name=payload.name,
        configuration=configuration,
        description=payload.description,
    )


@router.get(
    "/{dataset_id}/templates",
    response_model=list[ConfigurationTemplate],
    summary="List configuration templates for a dataset",
)
async def list_configuration_templates(dataset_id: str) -> list[ConfigurationTemplate]:
    _get_dataset_record(dataset_id)
    return list_templates(dataset_id)


@router.get(
    "/{dataset_id}/templates/{template_id}",
    response_model=ConfigurationTemplate,
    summary="Retrieve a specific configuration template",
)
async def read_configuration_template(dataset_id: str, template_id: str) -> ConfigurationTemplate:
    _get_dataset_record(dataset_id)
    template = get_template(dataset_id, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.post(
    "/{dataset_id}/templates/{template_id}/apply",
    response_model=DatasetConfiguration,
    summary="Apply a configuration template to a dataset",
)
async def apply_configuration_template(dataset_id: str, template_id: str) -> DatasetConfiguration:
    record = _get_dataset_record(dataset_id)
    template = get_template(dataset_id, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    try:
        return replace_configuration(dataset_id, template.configuration, record.profile)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete(
    "/{dataset_id}/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a configuration template",
)
async def delete_configuration_template(dataset_id: str, template_id: str) -> None:
    _get_dataset_record(dataset_id)
    delete_template(dataset_id, template_id)

