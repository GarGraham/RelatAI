"""Multivariate modeling utilities."""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import statsmodels.api as sm
from numpy.linalg import LinAlgError
from statsmodels.tools.sm_exceptions import PerfectSeparationError

from relat_ai.services.analysis.utils import AnalysisResult, ModelSummary


LOGGER = logging.getLogger(__name__)


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
        required_columns = [config.response, *config.predictors]
        missing_columns = [column for column in required_columns if column not in frame.columns]
        if missing_columns:
            LOGGER.warning(
                "Skipping regression for response '%s' due to missing columns: %s",
                config.response,
                ", ".join(missing_columns),
            )
            continue

        design = frame.loc[:, required_columns].dropna()
        if design.empty:
            continue

        y = design.pop(config.response)
        x = design
        if config.add_intercept:
            x = sm.add_constant(x, prepend=True, has_constant="add")

        try:
            model = sm.OLS(y, x).fit()
        except (ValueError, LinAlgError, PerfectSeparationError) as exc:
            LOGGER.warning(
                "Skipping regression for response '%s' due to model fitting error: %s",
                config.response,
                exc,
            )
            continue

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
