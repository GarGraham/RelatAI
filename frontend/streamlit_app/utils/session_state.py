"""Session state management utilities for the Streamlit application."""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st


def initialize_session_state() -> None:
    """
    Initialize session state with default values for the application.
    
    This should be called at the start of the main app to ensure
    all required state keys exist with sensible defaults.
    """
    # Dataset tracking
    if "current_dataset_id" not in st.session_state:
        st.session_state.current_dataset_id = None
    
    if "dataset_metadata" not in st.session_state:
        st.session_state.dataset_metadata = None
    
    if "dataset_profile" not in st.session_state:
        st.session_state.dataset_profile = None
    
    # Configuration state
    if "configuration" not in st.session_state:
        st.session_state.configuration = None
    
    if "preview_data" not in st.session_state:
        st.session_state.preview_data = None
    
    if "selected_template" not in st.session_state:
        st.session_state.selected_template = None
    
    # Analysis state
    if "analysis_mode" not in st.session_state:
        st.session_state.analysis_mode = "correlation"
    
    if "analysis_running" not in st.session_state:
        st.session_state.analysis_running = False
    
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    
    if "analysis_error" not in st.session_state:
        st.session_state.analysis_error = None
    
    # UI state
    if "show_advanced_options" not in st.session_state:
        st.session_state.show_advanced_options = False
    
    if "visualization_type" not in st.session_state:
        st.session_state.visualization_type = "heatmap"
    
    if "selected_variables" not in st.session_state:
        st.session_state.selected_variables = []
    
    # Cache
    if "cached_templates" not in st.session_state:
        st.session_state.cached_templates = []
    
    if "audit_logs" not in st.session_state:
        st.session_state.audit_logs = []


def get_state(key: str, default: Any = None) -> Any:
    """
    Safely retrieve a value from session state.
    
    Args:
        key: Session state key
        default: Default value if key doesn't exist
    
    Returns:
        Value from session state or default
    """
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """
    Set a value in session state.
    
    Args:
        key: Session state key
        value: Value to store
    """
    st.session_state[key] = value


def clear_state(key: str) -> None:
    """
    Remove a key from session state.
    
    Args:
        key: Session state key to remove
    """
    if key in st.session_state:
        del st.session_state[key]


def reset_analysis_state() -> None:
    """
    Reset all analysis-related state variables.
    
    Useful when starting a new analysis or switching datasets.
    """
    st.session_state.analysis_running = False
    st.session_state.analysis_results = None
    st.session_state.analysis_error = None


def load_dataset_context(dataset_id: str) -> None:
    """
    Set the current dataset context in session state.
    
    Args:
        dataset_id: Unique identifier for the dataset to load
    """
    st.session_state.current_dataset_id = dataset_id
    # Reset analysis state when switching datasets
    reset_analysis_state()


def has_active_dataset() -> bool:
    """
    Check if there is an active dataset loaded.
    
    Returns:
        True if a dataset is currently loaded, False otherwise
    """
    return (
        st.session_state.current_dataset_id is not None
        and st.session_state.dataset_metadata is not None
    )


def get_current_dataset_id() -> Optional[str]:
    """
    Get the currently active dataset ID.
    
    Returns:
        Dataset ID if one is active, None otherwise
    """
    return st.session_state.get("current_dataset_id")


def has_configuration() -> bool:
    """
    Check if there is an active configuration loaded.
    
    Returns:
        True if a configuration exists, False otherwise
    """
    config = st.session_state.get("configuration")
    return config is not None and isinstance(config, dict)


def get_configuration() -> Optional[dict]:
    """
    Get the current configuration dictionary.
    
    Returns:
        Configuration dictionary if exists, None otherwise
    """
    return st.session_state.get("configuration")


def update_configuration(updates: dict) -> None:
    """
    Update specific fields in the current configuration.
    
    Args:
        updates: Dictionary of configuration fields to update
    """
    config = get_configuration()
    if config is None:
        config = {}
    
    config.update(updates)
    set_state("configuration", config)


def reset_configuration() -> None:
    """
    Clear the current configuration state.
    """
    set_state("configuration", None)
    set_state("preview_data", None)
    set_state("selected_template", None)


def set_analysis_running(running: bool) -> None:
    """
    Set the analysis running state.
    
    Args:
        running: True if analysis is running, False otherwise
    """
    set_state("analysis_running", running)


def get_analysis_results() -> Optional[dict]:
    """
    Get the stored analysis results.
    
    Returns:
        Analysis results dictionary if exists, None otherwise
    """
    return st.session_state.get("analysis_results")


def set_analysis_results(results: Optional[dict]) -> None:
    """
    Store analysis results in session state.
    
    Args:
        results: Analysis results dictionary or None to clear
    """
    set_state("analysis_results", results)


def debug_state() -> None:
    """
    Display current session state for debugging purposes.
    
    Only displays if debug mode is enabled in configuration.
    Should be used in an expander or collapsible section.
    """
    from config import CONFIG
    
    if not CONFIG.debug_mode:
        return
    
    with st.expander("🐛 Debug: Session State", expanded=False):
        st.write("**Current Session State:**")
        
        # Group state keys by category
        categories = {
            "Dataset": ["current_dataset_id", "dataset_metadata", "dataset_profile"],
            "Configuration": ["configuration", "preview_data", "selected_template"],
            "Analysis": ["analysis_mode", "analysis_running", "analysis_results", "analysis_error"],
            "UI": ["show_advanced_options", "visualization_type", "selected_variables"],
            "Cache": ["cached_templates", "audit_logs"],
        }
        
        for category, keys in categories.items():
            st.write(f"**{category}:**")
            category_state = {
                key: st.session_state.get(key, "Not set")
                for key in keys
                if key in st.session_state
            }
            if category_state:
                st.json(category_state)
            else:
                st.write("  _(No state)_")


# =========================================================================
# Helper Functions for Phase 3+ Components
# =========================================================================

def get_selected_dataset() -> Optional[dict]:
    """
    Get the currently selected dataset metadata.
    
    Returns:
        Dictionary with dataset metadata including 'id', 'name', etc.
        None if no dataset is loaded.
    """
    dataset_id = get_current_dataset_id()
    dataset_metadata = get_state('dataset_metadata')
    
    if not dataset_id or not dataset_metadata:
        return None
    
    # Return standardized format expected by Analysis page
    return {
        'id': dataset_id,
        'name': dataset_metadata.get('filename', 'Unknown'),
        'row_count': dataset_metadata.get('row_count', 0),
        'column_count': dataset_metadata.get('column_count', 0),
    }


def get_analysis_mode() -> Optional[str]:
    """
    Get the currently selected analysis mode.
    
    Returns:
        Analysis mode string ('correlation', 'multivariate', 'auto_triage')
        or None if not configured.
    """
    config = get_configuration()
    if not config:
        return get_state('analysis_mode', 'correlation')
    
    return config.get('analysis_mode', 'correlation')


def get_current_config() -> Optional[dict]:
    """
    Get the current analysis configuration.
    
    Alias for get_configuration() for consistency with Analysis page expectations.
    
    Returns:
        Configuration dictionary or None if not configured.
    """
    return get_configuration()
