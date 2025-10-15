from __future__ import annotations

from relat_ai.services.analysis.auto_triage import AutoTriageConfig
from relat_ai.services.analysis_runner import _apply_auto_triage_guardrails


def test_guardrails_enforce_upper_bounds(monkeypatch) -> None:
    config = AutoTriageConfig(
        numeric_columns=["a", "b"],
        max_components=20,
        kmeans_clusters=50,
        hierarchical_clusters=40,
    )

    overrides: list[dict[str, int]] = []

    def fake_record(dataset_id: str, **payload):
        overrides.append(payload)

    monkeypatch.setattr(
        "relat_ai.services.analysis_runner.record_guardrail_override",
        fake_record,
    )

    _apply_auto_triage_guardrails("dataset", config)

    assert config.kmeans_clusters == 12
    assert config.hierarchical_clusters == 12
    assert config.max_components == 8
    assert {entry["guardrail"] for entry in overrides} == {
        "kmeans_clusters",
        "hierarchical_clusters",
        "max_components",
    }
