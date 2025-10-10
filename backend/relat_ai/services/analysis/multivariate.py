"""Multivariate modeling utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import statsmodels.api as sm

from relat_ai.services.analysis.utils import AnalysisResult, ModelSummary


@dataclass(slots=True)
class RegressionConfig:
    """Configuration for regression modeling."""

    response: str
    predictors: list[str]
    add_intercept: bool = True


def build_multivariate_models(
    frame: pd.DataFrame,
    configs: Iterable[RegressionConfig],
) -> AnalysisResult:
    """Fit regression models defined by the provided configurations."""

    summaries: list[ModelSummary] = []
    for config in configs:
        design = frame[[config.response] + config.predictors].dropna()
        if design.empty:
            continue

        y = design.pop(config.response)
        x = design
        if config.add_intercept:
            x = sm.add_constant(x, prepend=True, has_constant="add")

        model = sm.OLS(y, x).fit()
        summaries.append(
            ModelSummary(
                response=config.response,
                predictors=config.predictors,
                r_squared=float(model.rsquared),
                adjusted_r_squared=float(model.rsquared_adj),
                aic=float(model.aic),
                bic=float(model.bic),
            )
        )

    return AnalysisResult(models=summaries)
