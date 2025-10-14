from __future__ import annotations

import numpy as np
import pandas as pd

from relat_ai.core.autotriage_models import ChangePointReportModel, SignalDetail
from relat_ai.services.analysis.auto_triage import (
    AutoTriageConfig,
    SignalVector,
    compute_cluster_profile,
    _build_change_point_report,
)
from relat_ai.services.analysis.evidence_builder import build_evidence_bundle


def test_signal_vector_normalization_and_score() -> None:
    signals = {
        "A": {"pca_loading": 0.8, "changepoint": 3},
        "B": {"pca_loading": 0.5, "changepoint": 1},
        "C": {"pca_loading": 0.2, "changepoint": 0},
    }

    vector = SignalVector(target="A", raw_signals=signals["A"])
    vector.normalize(signals)
    score = vector.compute_weighted_score({"pca_loading": 0.6, "changepoint": 0.4})

    assert 0.5 < score <= 1.0
    bullets = vector.build_bullets()
    assert bullets
    assert all(isinstance(bullet, SignalDetail) for bullet in bullets)


def test_compute_cluster_profile_returns_expected_keys() -> None:
    np.random.seed(0)
    df = pd.DataFrame(
        {
            "feature_1": np.concatenate([np.random.normal(0, 1, 30), np.random.normal(5, 1, 30)]),
            "feature_2": np.random.normal(0, 1, 60),
        }
    )
    labels = np.array([0] * 30 + [1] * 30)

    profile = compute_cluster_profile(df, ["feature_1", "feature_2"], labels)

    assert profile.k == 2
    assert len(profile.sizes) == 2
    assert profile.top_diff_features
    assert profile.medoids


def test_build_change_point_report_segments() -> None:
    config = AutoTriageConfig(numeric_columns=["x"], max_components=1)
    series = pd.Series(np.concatenate([np.ones(20), np.ones(20) * 5]))
    frame = pd.DataFrame({"x": series})
    report = _build_change_point_report(
        frame=frame,
        series=series,
        column="x",
        method="cusum",
        locations=[20],
        config=config,
        cluster_labels=None,
        cluster_profile=None,
    )

    assert isinstance(report, ChangePointReportModel)
    assert report.segments
    assert report.indices == [20]


def test_evidence_bundle_round_trip() -> None:
    bundle = build_evidence_bundle(
        suspicion_items=[],
        pca=None,
        change_points=[],
        cluster_profile=None,
    )

    assert bundle.suspicion_items == []
    assert bundle.change_points == []
