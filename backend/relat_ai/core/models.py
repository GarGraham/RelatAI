"""Domain models shared across services."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from pydantic import ConfigDict, field_validator, model_validator


class DatasetMetadata(BaseModel):
    """Metadata captured for uploaded datasets."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataset_id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    path: Path = Field(exclude=True)
    original_filename: str | None = None
    content_type: str | None = None
    file_size_bytes: int | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    row_count: int | None = None
    column_count: int | None = None


class ColumnProfileModel(BaseModel):
    """Serialized representation of column-level profiling output."""

    name: str
    logical_type: str
    pandas_dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: list[Any]
    stats: dict[str, Any]


class DatasetProfileModel(BaseModel):
    """Serialized dataset-level profiling output."""

    dataset_id: str
    name: str
    row_count: int
    column_count: int
    missing_cell_count: int
    memory_usage_bytes: int
    columns: list[ColumnProfileModel]


class DatasetUploadResponse(BaseModel):
    """Response payload returned when a dataset is ingested and profiled."""

    metadata: DatasetMetadata
    profile: DatasetProfileModel


AnalysisMode = Literal["correlation", "multivariate", "auto_triage"]


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


class DatasetConfiguration(BaseModel):
    """Represents the user configuration controlling downstream analyses."""

    dataset_id: str
    selected_columns: list[str] = Field(default_factory=list)
    analysis_mode: AnalysisMode = "correlation"
    max_variables: int = 4
    interaction_depth: int = 2
    include_interactions: bool = True
    anchor_columns: list[str] = Field(default_factory=list)
    filters: dict[str, list[Any]] = Field(default_factory=dict)

    @field_validator("selected_columns", "anchor_columns", mode="before")
    @classmethod
    def _coerce_str_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        raise TypeError("Expected a list of strings")

    @field_validator("filters")
    @classmethod
    def _validate_filters(cls, value: dict[str, list[Any]]) -> dict[str, list[Any]]:
        normalised: dict[str, list[Any]] = {}
        for column, items in value.items():
            if not isinstance(items, list):
                raise TypeError("Filter values must be provided as a list")
            normalised[column] = items
        return normalised

    @model_validator(mode="after")
    def _validate_relationships(self) -> "DatasetConfiguration":
        self.selected_columns = _deduplicate(self.selected_columns)
        self.anchor_columns = _deduplicate(self.anchor_columns)
        if self.max_variables < 1:
            raise ValueError("max_variables must be at least 1")
        if self.interaction_depth < 1:
            raise ValueError("interaction_depth must be at least 1")
        missing_anchors = set(self.anchor_columns) - set(self.selected_columns)
        if missing_anchors:
            raise ValueError("Anchor columns must be included in selected_columns")
        return self


class ConfigurationUpdateRequest(BaseModel):
    """Partial update payload for dataset configuration settings.

    Filter semantics:
    - ``filters`` set to ``null`` leaves filters unchanged.
    - ``filters`` set to ``{}`` clears all existing filters.
    - ``filters`` populated with column keys replaces those specific filters.
    """

    selected_columns: list[str] | None = None
    analysis_mode: AnalysisMode | None = None
    max_variables: int | None = None
    interaction_depth: int | None = None
    include_interactions: bool | None = None
    anchor_columns: list[str] | None = None
    filters: dict[str, list[Any]] | None = None


class ConfigurationPreviewResponse(BaseModel):
    """Represents a preview of a dataset after configuration filters are applied."""

    dataset_id: str
    row_count: int
    columns: list[str]
    preview: list[dict[str, Any]]


class ConfigurationTemplateCreate(BaseModel):
    """Payload for creating configuration templates."""

    name: str
    description: str | None = None
    configuration: DatasetConfiguration | None = None


class ConfigurationTemplate(BaseModel):
    """Stored representation of a reusable configuration template."""

    template_id: str = Field(default_factory=lambda: uuid4().hex)
    dataset_id: str
    name: str
    description: str | None = None
    configuration: DatasetConfiguration
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditActionModel(BaseModel):
    """Serialized representation of a preprocessing action."""

    action_type: str
    timestamp: datetime
    details: dict[str, Any]
    column: str | None = None


class AuditLogModel(BaseModel):
    """Serialized audit log captured during dataset ingestion."""

    dataset_id: str
    dataset_name: str
    dataset_hash: str
    row_count: int
    column_count: int
    created_at: datetime
    actions: list[AuditActionModel]
