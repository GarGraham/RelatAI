"""Domain models shared across services."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetMetadata(BaseModel):
    """Metadata captured for uploaded datasets."""

    name: str
    path: Path
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    row_count: int | None = None
    column_count: int | None = None


class AnalysisRequest(BaseModel):
    """User-selected configuration for running correlation analyses."""

    target_columns: list[str]
    feature_columns: list[str]
    analysis_mode: Literal["pairwise", "multivariate", "hybrid"] = "pairwise"
    max_variables: int = 4
    include_interactions: bool = True
    anchor_columns: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
