"""Statistical analysis pipelines for RelatAI."""

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
    "PartialCorrelationRequest",
    "PairwiseAnalysisPlan",
    "RegressionConfig",
    "RegressionPlan",
    "compute_pairwise_correlations",
    "build_multivariate_models",
]
