"""Utility modules for the Streamlit application."""

from utils.api_client import APIError, RelatAIClient, get_client, handle_api_error
from utils.session_state import (
    clear_state,
    debug_state,
    get_analysis_mode,
    get_analysis_results,
    get_configuration,
    get_current_config,
    get_current_dataset_id,
    get_selected_dataset,
    get_state,
    has_active_dataset,
    has_configuration,
    initialize_session_state,
    load_dataset_context,
    reset_analysis_state,
    reset_configuration,
    set_analysis_results,
    set_analysis_running,
    set_state,
    update_configuration,
)
from utils.autotriage_state import (
    AutoTriageState,
    TabName,
    get_autotriage_state,
    set_active_autotriage_tab,
    clear_autotriage_selections,
    get_navigation_from_link,
    render_navigation_breadcrumb,
)
from utils.navigation import (
    navigate,
    get_query_params,
    set_query_params,
    sync_state_from_url,
    clear_query_params,
    get_shareable_link,
    render_share_button,
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
    "get_current_config",
    "update_configuration",
    "reset_configuration",
    "debug_state",
    # Analysis helpers
    "get_selected_dataset",
    "get_analysis_mode",
    "get_analysis_results",
    "set_analysis_results",
    "set_analysis_running",
    # Auto-triage state management
    "AutoTriageState",
    "TabName",
    "get_autotriage_state",
    "set_active_autotriage_tab",
    "clear_autotriage_selections",
    "get_navigation_from_link",
    "render_navigation_breadcrumb",
    # Navigation and deep-linking
    "navigate",
    "get_query_params",
    "set_query_params",
    "sync_state_from_url",
    "clear_query_params",
    "get_shareable_link",
    "render_share_button",
]
