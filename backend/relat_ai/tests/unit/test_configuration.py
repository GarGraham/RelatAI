"""Unit tests covering the configuration and template services."""

from __future__ import annotations

import pandas as pd
import pytest

from relat_ai.core.models import ConfigurationUpdateRequest, DatasetConfiguration
from relat_ai.services import configuration, schema_detection, templates


def _make_profile(dataset_id: str, columns: list[str]) -> schema_detection.DatasetProfile:
    column_profiles = [
        schema_detection.ColumnProfile(
            name=name,
            logical_type="categorical",
            pandas_dtype="object",
            non_null_count=10,
            null_count=0,
            unique_count=3,
            sample_values=["sample"],
            stats={},
        )
        for name in columns
    ]
    return schema_detection.DatasetProfile(
        dataset_id=dataset_id,
        name="dataset",
        row_count=10,
        column_count=len(columns),
        missing_cell_count=0,
        memory_usage_bytes=1024,
        columns=column_profiles,
    )


@pytest.fixture(autouse=True)
def _reset_configuration_state() -> None:
    configuration.reset_store()
    templates.reset_templates()
    yield
    configuration.reset_store()
    templates.reset_templates()


def test_initialise_configuration_defaults_to_profile_columns() -> None:
    profile = _make_profile("ds", ["a", "b", "c"])
    config = configuration.initialise_configuration("ds", profile)

    assert config.dataset_id == "ds"
    assert config.selected_columns == ["a", "b", "c"]
    assert config.analysis_mode == "correlation"


def test_update_configuration_validates_columns() -> None:
    profile = _make_profile("ds", ["region", "value"])
    configuration.initialise_configuration("ds", profile)

    update = ConfigurationUpdateRequest(
        selected_columns=["region"],
        anchor_columns=["region"],
        filters={"region": ["Europe"]},
        max_variables=1,
    )
    config = configuration.update_configuration("ds", update, profile)

    assert config.selected_columns == ["region"]
    assert config.anchor_columns == ["region"]
    assert config.filters == {"region": ["Europe"]}

    invalid = ConfigurationUpdateRequest(selected_columns=["missing"])
    with pytest.raises(ValueError):
        configuration.update_configuration("ds", invalid, profile)


def test_apply_configuration_to_frame_filters_rows() -> None:
    profile = _make_profile("ds", ["Region", "Value"])
    configuration.initialise_configuration("ds", profile)
    configuration.update_configuration(
        "ds", ConfigurationUpdateRequest(filters={"Region": ["Europe"]}), profile
    )

    frame = pd.DataFrame({"Region": ["Europe", "Asia"], "Value": [1, 2]})
    config = configuration.get_configuration("ds")
    assert config is not None

    filtered = configuration.apply_configuration_to_frame(frame, config)

    assert filtered.shape == (1, 2)
    assert filtered.iloc[0]["Region"] == "Europe"


def test_normalise_configuration_enforces_anchor_membership() -> None:
    profile = _make_profile("ds", ["a", "b"])
    base = DatasetConfiguration.model_construct(
        dataset_id="other",
        selected_columns=["a"],
        anchor_columns=["b"],
        analysis_mode="correlation",
        max_variables=1,
        interaction_depth=1,
        include_interactions=True,
        filters={},
    )

    with pytest.raises(ValueError):
        configuration.normalise_configuration("ds", base, profile)


def test_template_store_returns_isolated_copies() -> None:
    profile = _make_profile("ds", ["x", "y"])
    config = configuration.initialise_configuration("ds", profile)
    template = templates.create_template(dataset_id="ds", name="default", configuration=config)

    template.configuration.selected_columns.append("z")
    stored = templates.get_template("ds", template.template_id)
    assert stored is not None
    assert stored.configuration.selected_columns == ["x", "y"]


def test_configuration_history_records_changes() -> None:
    profile = _make_profile("ds", ["alpha", "beta"])
    configuration.initialise_configuration("ds", profile)

    initial_history = configuration.list_configuration_versions("ds")
    assert len(initial_history) == 1
    assert initial_history[0].version == 1
    assert initial_history[0].configuration.selected_columns == ["alpha", "beta"]

    configuration.update_configuration(
        "ds", ConfigurationUpdateRequest(filters={"alpha": ["A"]}), profile
    )

    history = configuration.list_configuration_versions("ds")
    assert len(history) == 2
    latest = history[-1]
    assert latest.version == 2
    assert latest.configuration.filters == {"alpha": ["A"]}
    assert latest.changes["filters"] == ({}, {"alpha": ["A"]})


def test_restore_configuration_version_reverts_state() -> None:
    profile = _make_profile("ds", ["x", "y"])
    configuration.initialise_configuration("ds", profile)
    configuration.update_configuration(
        "ds", ConfigurationUpdateRequest(selected_columns=["x"]), profile
    )

    configuration.restore_configuration_version("ds", version=1)
    restored = configuration.get_configuration("ds")
    assert restored is not None
    assert restored.selected_columns == ["x", "y"]

    history = configuration.list_configuration_versions("ds")
    assert len(history) == 3
    assert history[-1].changes["selected_columns"] == (["x"], ["x", "y"])
