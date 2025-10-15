"""Utilities for loading dynamic configuration artefacts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from relat_ai.core.config import get_settings

_DEFAULT_PRESETS: dict[str, Any] = {
    "auto_triage": {
        "suspicion_weights": {
            "pca_loading": 0.35,
            "changepoint": 0.25,
            "cluster": 0.2,
            "residual": 0.1,
            "dispersion": 0.1,
        },
        "suspicion_top_k": 5,
    }
}

_ALLOWED_WEIGHT_KEYS = frozenset(
    {"pca_loading", "changepoint", "cluster", "residual", "dispersion"}
)


class VisualizationPresetsError(RuntimeError):
    """Raised when visualization presets cannot be loaded or validated."""


def _resolve_path() -> Path:
    settings = get_settings()
    return settings.visualization_preset_path


@lru_cache(maxsize=1)
def get_visualization_presets() -> dict[str, Any]:
    """Return visualization presets loaded from the configured YAML file."""

    path = _resolve_path()
    if not path.exists():
        return _DEFAULT_PRESETS

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive logging
        raise VisualizationPresetsError(f"Failed to parse visualization presets: {exc}") from exc

    if not isinstance(payload, dict):
        raise VisualizationPresetsError("Visualization presets must be a mapping")

    merged = _DEFAULT_PRESETS | payload
    auto_triage = merged.setdefault("auto_triage", {})
    weights = auto_triage.get("suspicion_weights")
    if weights is None:
        auto_triage["suspicion_weights"] = _DEFAULT_PRESETS["auto_triage"]["suspicion_weights"].copy()
    elif not isinstance(weights, dict):
        raise VisualizationPresetsError("suspicion_weights must be a mapping of signal weights")
    else:
        invalid = set(weights) - _ALLOWED_WEIGHT_KEYS
        if invalid:
            raise VisualizationPresetsError(
                f"Unsupported suspicion weight keys: {sorted(invalid)!r}"
            )
        auto_triage["suspicion_weights"] = {
            key: float(value)
            for key, value in weights.items()
            if key in _ALLOWED_WEIGHT_KEYS
        }
    if "suspicion_top_k" not in auto_triage:
        auto_triage["suspicion_top_k"] = _DEFAULT_PRESETS["auto_triage"]["suspicion_top_k"]

    return merged


def get_auto_triage_weights() -> dict[str, float]:
    """Return normalized suspicion weights for auto-triage scoring."""

    presets = get_visualization_presets()["auto_triage"]["suspicion_weights"]
    total = sum(presets.values())
    if total <= 0:
        return _DEFAULT_PRESETS["auto_triage"]["suspicion_weights"].copy()
    return {key: value / total for key, value in presets.items()}


def get_auto_triage_suspicion_top_k() -> int:
    """Return the configured suspicion ranking cutoff."""

    raw = get_visualization_presets()["auto_triage"].get("suspicion_top_k", 5)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 5
    return max(1, value)
