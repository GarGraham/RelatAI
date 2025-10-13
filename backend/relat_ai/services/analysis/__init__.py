"""Statistical analysis pipelines for RelatAI."""

from .auto_triage import AutoTriageConfig, AutoTriageResult, run_auto_triage
from .pairwise import PairwiseAnalysisPlan, compute_pairwise_correlations
from .multivariate import (
    ANOVAConfig,
    PartialCorrelationRequest,
    RegressionConfig,
    RegressionPlan,
    build_multivariate_models,
)
from .utils import AnalysisResult

__all__ = [
    "ANOVAConfig",
    "AnalysisResult",
    "AutoTriageConfig",
    "AutoTriageResult",
    "PartialCorrelationRequest",
    "PairwiseAnalysisPlan",
    "RegressionConfig",
    "RegressionPlan",
    "compute_pairwise_correlations",
    "build_multivariate_models",
    "run_auto_triage",
]
