"""Telemetry helpers for capturing lightweight UX metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import streamlit as st

from config import CONFIG


def _extract_web_vitals(user_info: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not user_info:
        return None
    browser = user_info.get("browser") if isinstance(user_info, dict) else None
    if not isinstance(browser, dict):
        return None
    metrics = browser.get("metrics")
    if isinstance(metrics, dict) and metrics.get("web_vitals"):
        return metrics["web_vitals"]
    if isinstance(metrics, dict):
        return metrics
    return None


def capture_web_vitals(event: str, *, dataset_id: str | None = None) -> None:
    """Persist Core Web Vitals metrics if available from Streamlit."""

    vitals = _extract_web_vitals(st.experimental_user_info())
    if not vitals:
        return

    log_path = Path(CONFIG.analytics_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event": event,
        "dataset_id": dataset_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vitals": vitals,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
