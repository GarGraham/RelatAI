"""Utility modules for the Streamlit application."""

from utils.api_client import APIError, RelatAIClient, get_client, handle_api_error
from utils.session_state import (
    clear_state,
    debug_state,
    get_configuration,
    get_current_dataset_id,
    get_state,
    has_active_dataset,
    has_configuration,
    initialize_session_state,
    load_dataset_context,
    reset_analysis_state,
    reset_configuration,
    set_state,
    update_configuration,
)

__all__ = [
    # API client
    "APIError",
    "RelatAIClient",
    "get_client",
    "handle_api_error",
    # Session state
    "initialize_session_state",
    "get_state",
    "set_state",
    "clear_state",
    "reset_analysis_state",
    "load_dataset_context",
    "has_active_dataset",
    "get_current_dataset_id",
    "has_configuration",
    "get_configuration",
    "update_configuration",
    "reset_configuration",
    "debug_state",
]
