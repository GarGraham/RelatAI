from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from relat_ai.services.analysis.auto_triage import AutoTriageConfig, run_auto_triage


@pytest.mark.autotriage_e2e
def test_autotriage_contract_playwright() -> None:
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    rng = np.random.default_rng(321)
    frame = pd.DataFrame(
        {
            "metric_a": rng.normal(0, 1, size=120),
            "metric_b": np.concatenate([rng.normal(0, 1, size=60), rng.normal(4, 1, size=60)]),
            "metric_c": rng.normal(1, 0.5, size=120),
        }
    )

    config = AutoTriageConfig(numeric_columns=["metric_a", "metric_b", "metric_c"], max_components=2)
    result = run_auto_triage(frame, config)

    payload = {
        "suspicion": [score.target for score in result.suspicion_rankings],
        "components": len(result.pca_components),
        "clusters": len(result.clusters),
    }

    with sync_playwright() as playwright:  # type: ignore[attr-defined]
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        contract = page.evaluate(
            "payload => ({\n                hasSuspicion: payload.suspicion.length > 0,\n                componentCount: payload.components,\n                clusterCount: payload.clusters\n            })",
            payload,
        )
        browser.close()

    assert contract["hasSuspicion"] is True
    assert contract["componentCount"] == len(result.pca_components)
    assert contract["clusterCount"] == len(result.clusters)
