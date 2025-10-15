from __future__ import annotations

from math import isclose

import pytest

hypothesis = pytest.importorskip("hypothesis")
st = hypothesis.strategies
given = hypothesis.given

from relat_ai.services.analysis.auto_triage import SignalVector


@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=5),
        values=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=5,
    )
)
def test_signal_vector_percentile_normalisation(signals: dict[str, float]) -> None:
    vector = SignalVector(target="feature", raw_signals=signals.copy())
    vector.normalize({"feature": signals})
    assert set(vector.normalized_signals) == set(signals)
    for value in vector.normalized_signals.values():
        assert 0.0 <= value <= 1.0


@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=5),
        values=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=5,
    ),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=5),
        values=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=5,
    ),
)
def test_signal_vector_weighted_score_is_bounded(
    raw_signals: dict[str, float], weights: dict[str, float]
) -> None:
    vector = SignalVector(target="feature", raw_signals=raw_signals.copy())
    population = {"feature": raw_signals}
    vector.normalize(population)
    vector.compute_weighted_score(weights)
    assert 0.0 <= vector.weighted_score <= 1.0 or isclose(vector.weighted_score, 0.0)
