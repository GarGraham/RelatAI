"""Tests for visualization helpers."""

from relat_ai.services.analysis.utils import AnalysisResult, CorrelationRecord
from relat_ai.services.visualization import build_correlation_heatmap


def test_build_correlation_heatmap_extends_bundle() -> None:
    """Heatmap helper should populate heatmap, network, and link summaries."""

    result = AnalysisResult(
        correlations=[
            CorrelationRecord(
                variables=("a", "b"),
                coefficient=0.9,
                p_value=0.01,
                sample_size=100,
                method="pearson",
            ),
            CorrelationRecord(
                variables=("b", "c"),
                coefficient=-0.4,
                p_value=0.05,
                sample_size=100,
                method="pearson",
            ),
        ]
    )

    bundle = build_correlation_heatmap(result)

    assert bundle.heatmap is not None
    assert len(bundle.heatmap.cells) == 2
    assert bundle.network is not None
    assert {node.id for node in bundle.network.nodes} == {"a", "b", "c"}
    assert len(bundle.network.edges) == 2
    assert bundle.strongest_links
    assert bundle.strongest_links[0].value == 0.9
