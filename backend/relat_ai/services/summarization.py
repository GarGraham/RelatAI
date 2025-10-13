"""Placeholder summarization service integrating with LLM providers."""

from __future__ import annotations

import math

from dataclasses import asdict
from typing import Iterable

from relat_ai.services.analysis.utils import AnalysisResult, CorrelationRecord, ModelSummary


class SummarizationService:
    """Produce human-readable narratives from structured statistical outputs."""

    def summarize(self, result: AnalysisResult) -> str:
        """Generate a plain-text summary suitable for Streamlit rendering."""

        sections: list[str] = []
        if result.correlations:
            sections.append(self._summarize_correlations(result.correlations))
        if result.models:
            sections.append(self._summarize_models(result.models))
        if not sections:
            return "No analysis results available."
        return "\n\n".join(sections)

    def _summarize_correlations(self, correlations: Iterable[CorrelationRecord]) -> str:
        bullets = []
        for record in correlations:
            variables = f"{record.variables[0]} vs {record.variables[1]}"
            metrics = [f"coeff={record.coefficient:.3f}"]
            if record.p_value is not None:
                metrics.append(f"p={record.p_value:.3g}")
            if record.statistic is not None and record.method not in {"pearson", "spearman", "kendall", "point_biserial", "cramers_v"}:
                metrics.append(f"stat={record.statistic:.3g}")
            metrics.append(f"n={record.sample_size}")
            bullets.append(f"{variables}: {', '.join(metrics)} ({record.method})")
        if not bullets:
            return "No pairwise correlations computed."
        return "Pairwise correlations:\n- " + "\n- ".join(bullets)

    def _summarize_models(self, models: Iterable[ModelSummary]) -> str:
        bullets = []
        for model in models:
            predictors = ", ".join(model.predictors)
            metrics = []
            for name, value in asdict(model.metrics).items():
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    continue
                metrics.append(f"{name}={value:.3f}")
            detail = ", ".join(metrics) if metrics else "no metrics"
            bullets.append(f"{model.model_type}: {model.response} ~ {predictors} | {detail}")
        if not bullets:
            return "No multivariate models computed."
        return "Multivariate models:\n- " + "\n- ".join(bullets)
