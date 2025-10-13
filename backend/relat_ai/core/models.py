"""Domain models shared across services."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from pydantic import ConfigDict


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


class AnalysisRequest(BaseModel):
    """User-selected configuration for running correlation analyses."""

    target_columns: list[str]
    feature_columns: list[str]
    analysis_mode: Literal["pairwise", "multivariate", "hybrid"] = "pairwise"
    max_variables: int = 4
    include_interactions: bool = True
    anchor_columns: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


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
