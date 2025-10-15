"""Centralized navigation routing and deep-linking for Streamlit application.

Provides URL query parameter support and state synchronization for
auto-triage deep-linking functionality.
"""

from __future__ import annotations

import streamlit as st
from typing import Dict, Any, Optional
from urllib.parse import urlencode

from utils.autotriage_state import (
    get_autotriage_state,
    set_active_autotriage_tab,
    TabName,
)


def navigate(payload: Dict[str, Any]) -> None:
    """Interpret navigation payload and update application state.
    
    This function serves as the central routing mechanism for deep-linking.
    It accepts a payload dictionary (typically from backend link_registry
    entries or UI click handlers) and updates the appropriate state.
    
    Args:
        payload: Navigation dictionary with keys:
            - 'tab': Target tab name (required)
            - 'context': Additional context dict (optional)
            - 'source': Source tab (optional)
            
    Example:
        >>> # Navigate to PCA component 2
        >>> navigate({
        ...     'tab': 'pca',
        ...     'context': {'component': 2},
        ...     'source': 'suspicion'
        ... })
    """
    if not payload or "tab" not in payload:
        return
    
    tab = payload["tab"]
    context = payload.get("context")
    source = payload.get("source")
    
    # Validate tab name
    valid_tabs: list[TabName] = ["suspicion", "pca", "changepoints", "clusters"]
    if tab not in valid_tabs:
        st.warning(f"Invalid tab: {tab}")
        return
    
    set_active_autotriage_tab(tab, context, source)


def get_query_params() -> Dict[str, Any]:
    """Extract navigation parameters from URL query string.
    
    Streamlit's query_params provides URL parameters for deep-linking.
    This function parses them into a navigation payload.
    
    Returns:
        Dictionary with parsed parameters, or empty dict if none
        
    Example URL:
        ?tab=pca&component=1&source=suspicion
    """
    try:
        # Streamlit 1.30+ uses st.query_params (dict-like)
        query_params = st.query_params
        
        if not query_params:
            return {}
        
        # Extract recognized parameters
        payload: Dict[str, Any] = {}
        
        if "tab" in query_params:
            payload["tab"] = query_params["tab"]
        
        # Build context from known keys
        context = {}
        if "component" in query_params:
            try:
                context["component"] = int(query_params["component"])
            except ValueError:
                pass
        if "column" in query_params:
            context["column"] = query_params["column"]
        if "cluster_id" in query_params:
            try:
                context["cluster_id"] = int(query_params["cluster_id"])
            except ValueError:
                pass
        if "target" in query_params:
            context["target"] = query_params["target"]
        
        if context:
            payload["context"] = context
        
        if "source" in query_params:
            payload["source"] = query_params["source"]
        
        return payload
    
    except Exception as e:
        # Fallback for older Streamlit versions or errors
        st.warning(f"Could not parse query parameters: {e}")
        return {}


def set_query_params(tab: TabName, context: Optional[Dict[str, Any]] = None) -> None:
    """Update URL query parameters to reflect current navigation state.
    
    This enables shareable deep-links. Users can copy the URL and return
    to the same view later.
    
    Args:
        tab: Active tab name
        context: Optional context dictionary
        
    Example:
        >>> set_query_params("pca", {"component": 2})
        # URL becomes: ?tab=pca&component=2
    """
    try:
        params = {"tab": tab}
        
        if context:
            if "component" in context:
                params["component"] = str(context["component"])
            if "column" in context:
                params["column"] = context["column"]
            if "cluster_id" in context:
                params["cluster_id"] = str(context["cluster_id"])
            if "target" in context:
                params["target"] = context["target"]
        
        st.query_params.update(params)
    
    except Exception as e:
        # Non-critical failure - navigation still works without URL updates
        pass


def sync_state_from_url() -> None:
    """Synchronize application state from URL query parameters.
    
    This should be called once during page load to restore state from
    deep-link URLs. It checks for query parameters and updates the
    AutoTriageState accordingly.
    
    Example:
        >>> # In app.py or page initialization
        >>> sync_state_from_url()
    """
    payload = get_query_params()
    
    if payload and "tab" in payload:
        state = get_autotriage_state()
        
        # Only sync if we're not already in the target state
        if state.active_tab != payload["tab"]:
            navigate(payload)


def clear_query_params() -> None:
    """Remove all navigation query parameters from URL.
    
    Useful when resetting to overview mode or clearing filters.
    """
    try:
        st.query_params.clear()
    except Exception:
        pass


def get_shareable_link(tab: TabName, context: Optional[Dict[str, Any]] = None) -> str:
    """Generate a shareable URL for current navigation state.
    
    This constructs a full URL (relative to app root) that can be
    copied to clipboard for sharing specific views.
    
    Args:
        tab: Target tab
        context: Optional context dictionary
        
    Returns:
        URL string with query parameters
        
    Example:
        >>> link = get_shareable_link("pca", {"component": 2})
        >>> st.code(link, language="text")
    """
    params = {"tab": tab}
    
    if context:
        if "component" in context:
            params["component"] = str(context["component"])
        if "column" in context:
            params["column"] = context["column"]
        if "cluster_id" in context:
            params["cluster_id"] = str(context["cluster_id"])
        if "target" in context:
            params["target"] = context["target"]
    
    query_string = urlencode(params)
    return f"?{query_string}"


def render_share_button(tab: TabName, context: Optional[Dict[str, Any]] = None) -> None:
    """Render a button that copies shareable link to clipboard.
    
    Args:
        tab: Current tab name
        context: Current context dictionary
    """
    link = get_shareable_link(tab, context)
    
    # Use Streamlit's button with a unique key
    if st.button("📋 Copy Link", key=f"share_{tab}", help="Copy shareable link to clipboard"):
        # Display the link for manual copying
        # (Clipboard API requires components.html which may not work in all environments)
        st.code(link, language="text")
        st.success("Link displayed above - copy manually")


__all__ = [
    "navigate",
    "get_query_params",
    "set_query_params",
    "sync_state_from_url",
    "clear_query_params",
    "get_shareable_link",
    "render_share_button",
]
