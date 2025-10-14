"""Narrative composition utilities for auto-triage evidence bundles."""

from __future__ import annotations

from typing import Iterable, Optional

from relat_ai.core.autotriage_models import (
    ChangePointReportModel,
    ClusterProfileModel,
    EvidenceBundle,
    PCAExplainModel,
    SuspicionItemModel,
)


def build_evidence_bundle(
    *,
    suspicion_items: Iterable[SuspicionItemModel],
    pca: Optional[PCAExplainModel],
    change_points: Iterable[ChangePointReportModel],
    cluster_profile: Optional[ClusterProfileModel] = None,
) -> EvidenceBundle:
    """Aggregate structured outputs into a single evidence payload."""

    suspicion_list = list(suspicion_items)
    change_point_list = list(change_points)

    return EvidenceBundle(
        suspicion_items=suspicion_list,
        pca=pca,
        change_points=change_point_list,
        clusters=cluster_profile,
    )


__all__ = ["build_evidence_bundle"]

