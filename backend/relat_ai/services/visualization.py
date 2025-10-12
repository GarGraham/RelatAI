"""Visualization metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from relat_ai.services.analysis.utils import AnalysisResult


HEATMAP_COMPATIBLE_METHODS = {
    "pearson",
    "spearman",
    "kendall",
    "point_biserial",
    "cramers_v",
}


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
    network: "CorrelationNetwork" | None = None
    strongest_links: list[HeatmapCell] = field(default_factory=list)


@dataclass(slots=True)
class GraphNode:
    """Node descriptor for network-style visualisations."""

    id: str
    label: str


@dataclass(slots=True)
class GraphEdge:
    """Edge descriptor for pairwise relationship networks."""

    source: str
    target: str
    weight: float


@dataclass(slots=True)
class CorrelationNetwork:
    """Network representation of correlations."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]


def build_correlation_heatmap(result: AnalysisResult) -> VisualizationBundle:
    """Convert pairwise correlation results into heatmap data."""

    correlations = [
        record
        for record in (result.correlations or [])
        if record.method in HEATMAP_COMPATIBLE_METHODS
    ]
    if not correlations:
        return VisualizationBundle(heatmap=None, network=None)

    cells: list[HeatmapCell] = [
        HeatmapCell(x=record.variables[0], y=record.variables[1], value=record.coefficient)
        for record in correlations
    ]
    network = _build_network_from_cells(cells)
    strongest_links = _select_strongest_links(cells)
    return VisualizationBundle(
        heatmap=Heatmap(title="Correlation Matrix", cells=cells),
        network=network,
        strongest_links=strongest_links,
    )


def _build_network_from_cells(cells: Iterable[HeatmapCell]) -> CorrelationNetwork:
    node_names = sorted({cell.x for cell in cells} | {cell.y for cell in cells})
    nodes = [GraphNode(id=name, label=name) for name in node_names]
    edges = [
        GraphEdge(source=cell.x, target=cell.y, weight=abs(cell.value)) for cell in cells
    ]
    return CorrelationNetwork(nodes=nodes, edges=edges)


def _select_strongest_links(cells: Iterable[HeatmapCell], limit: int = 5) -> list[HeatmapCell]:
    sorted_cells = sorted(cells, key=lambda cell: abs(cell.value), reverse=True)
    return sorted_cells[:limit]
