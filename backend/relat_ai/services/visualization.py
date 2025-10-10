"""Visualization metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass

from relat_ai.services.analysis.utils import AnalysisResult


@dataclass(slots=True)
class HeatmapCell:
    """Metadata describing a single heatmap cell."""

    x: str
    y: str
    value: float


@dataclass(slots=True)
class Heatmap:
    """Heatmap structure consumable by frontend visualizations."""

    title: str
    cells: list[HeatmapCell]


@dataclass(slots=True)
class VisualizationBundle:
    """Collection of visualization-ready payloads."""

    heatmap: Heatmap | None = None


def build_correlation_heatmap(result: AnalysisResult) -> VisualizationBundle:
    """Convert pairwise correlation results into heatmap data."""

    if not result.correlations:
        return VisualizationBundle(heatmap=None)

    cells = [
        HeatmapCell(x=record.variables[0], y=record.variables[1], value=record.coefficient)
        for record in result.correlations
    ]
    return VisualizationBundle(
        heatmap=Heatmap(title="Correlation Matrix", cells=cells),
    )
