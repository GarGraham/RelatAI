"""Placeholder summarization service integrating with LLM providers."""

from __future__ import annotations

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
        bullets = [
            f"{a} vs {b}: coeff={coef:.3f}, p={p_value:.3g}, n={sample_size} ({method})"
            for a, b, coef, p_value, sample_size, method in (
                (
                    record.variables[0],
                    record.variables[1],
                    record.coefficient,
                    record.p_value,
                    record.sample_size,
                    record.method,
                )
                for record in correlations
            )
        ]
        if not bullets:
            return "No pairwise correlations computed."
        return "Pairwise correlations:\n- " + "\n- ".join(bullets)

    def _summarize_models(self, models: Iterable[ModelSummary]) -> str:
        bullets = [
            f"{model.response} ~ {', '.join(model.predictors)} | R^2={model.r_squared:.3f}, adj R^2={model.adjusted_r_squared:.3f}"
            for model in models
        ]
        if not bullets:
            return "No multivariate models computed."
        return "Multivariate models:\n- " + "\n- ".join(bullets)
