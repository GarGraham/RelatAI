"""Auto-triage state management for navigation and drill-down context.

Provides centralized state management for the auto-triage analysis tabs,
enabling deep-linking, context preservation across tab switches, and
coordinated navigation between suspicion rankings, PCA, change-points,
and cluster views.
"""

from __future__ import annotations

import streamlit as st
from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Any


# Type alias for tab names
TabName = Literal["suspicion", "pca", "changepoints", "clusters"]


@dataclass
class AutoTriageState:
    """Centralized state for auto-triage tab navigation and drill-downs.
    
    This dataclass maintains the active tab, selected entities within each
    tab, and contextual drill-down information to support seamless navigation
    between related insights.
    
    Attributes:
        active_tab: Currently visible tab
        selected_suspicion_target: Column name selected in suspicion rankings
        selected_pca_component: PC index (1-based) selected in PCA tab
        selected_changepoint_column: Column with change-points being viewed
        selected_cluster_id: Cluster ID (0-based) selected in clusters tab
        drill_down_context: Additional context for cross-tab navigation
        last_navigation_source: Tab that triggered most recent navigation
    """
    
    active_tab: TabName = "suspicion"
    selected_suspicion_target: Optional[str] = None
    selected_pca_component: Optional[int] = None
    selected_changepoint_column: Optional[str] = None
    selected_cluster_id: Optional[int] = None
    drill_down_context: Dict[str, Any] = field(default_factory=dict)
    last_navigation_source: Optional[TabName] = None
    
    def navigate_to(
        self,
        tab: TabName,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[TabName] = None
    ) -> None:
        """Navigate to a specific tab with optional context.
        
        Args:
            tab: Target tab to navigate to
            context: Optional dictionary with tab-specific context:
                - For 'pca': {'component': int} - PC number (1-based)
                - For 'changepoints': {'column': str} - Column name
                - For 'clusters': {'cluster_id': int} - Cluster ID (0-based)
                - For 'suspicion': {'target': str} - Column name
            source: Tab initiating the navigation (for breadcrumb tracking)
        """
        self.last_navigation_source = source if source else self.active_tab
        self.active_tab = tab
        
        if context:
            self.drill_down_context.update(context)
            
            # Update specific selection fields based on context
            if "component" in context:
                self.selected_pca_component = context["component"]
            if "column" in context:
                self.selected_changepoint_column = context["column"]
            if "cluster_id" in context:
                self.selected_cluster_id = context["cluster_id"]
            if "target" in context:
                self.selected_suspicion_target = context["target"]
    
    def clear_context(self) -> None:
        """Clear all navigation context and selections."""
        self.selected_suspicion_target = None
        self.selected_pca_component = None
        self.selected_changepoint_column = None
        self.selected_cluster_id = None
        self.drill_down_context.clear()
        self.last_navigation_source = None
    
    def get_breadcrumb(self) -> Optional[str]:
        """Generate a breadcrumb string for current navigation state.
        
        Returns:
            Human-readable breadcrumb describing current selection, or None
        """
        if self.active_tab == "suspicion" and self.selected_suspicion_target:
            return f"Suspicion: {self.selected_suspicion_target}"
        elif self.active_tab == "pca" and self.selected_pca_component:
            return f"PCA: PC{self.selected_pca_component}"
        elif self.active_tab == "changepoints" and self.selected_changepoint_column:
            return f"Change Points: {self.selected_changepoint_column}"
        elif self.active_tab == "clusters" and self.selected_cluster_id is not None:
            return f"Cluster: {self.selected_cluster_id}"
        return None


def get_autotriage_state() -> AutoTriageState:
    """Get or initialize auto-triage state from session state.
    
    This function ensures a single AutoTriageState instance exists in
    Streamlit's session state for the duration of the user session.
    
    Returns:
        AutoTriageState instance from session state
    """
    if "autotriage_state" not in st.session_state:
        st.session_state["autotriage_state"] = AutoTriageState()
    return st.session_state["autotriage_state"]


def set_active_autotriage_tab(
    tab: TabName,
    context: Optional[Dict[str, Any]] = None,
    source: Optional[TabName] = None
) -> None:
    """Set active tab and optional drill-down context.
    
    This is a convenience function that updates the session state and
    can be used as a callback for navigation buttons/links.
    
    Args:
        tab: Target tab name
        context: Optional context dictionary for the target tab
        source: Source tab initiating navigation (for tracking)
        
    Example:
        >>> # Navigate from suspicion to PCA component 1
        >>> set_active_autotriage_tab(
        ...     "pca",
        ...     context={"component": 1},
        ...     source="suspicion"
        ... )
    """
    state = get_autotriage_state()
    state.navigate_to(tab, context, source)


def clear_autotriage_selections() -> None:
    """Clear all navigation context and selections.
    
    Useful for "reset" or "back to overview" actions.
    """
    state = get_autotriage_state()
    state.clear_context()


def get_navigation_from_link(link_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse backend link data into navigation parameters.
    
    Backend signals (SuspicionItemModel.links, SignalDetail.link) provide
    navigation hints as dictionaries. This function translates them into
    parameters suitable for set_active_autotriage_tab().
    
    Args:
        link_data: Dictionary from backend with keys like:
            - {'tab': 'pca', 'component': 1}
            - {'tab': 'changepoints', 'column': 'Voltage_A'}
            - {'tab': 'clusters', 'feature': 'Temperature'}
    
    Returns:
        Dictionary with 'tab' and 'context' keys, or None if invalid
        
    Example:
        >>> link = {"tab": "pca", "component": 1}
        >>> nav_params = get_navigation_from_link(link)
        >>> set_active_autotriage_tab(**nav_params)
    """
    if not link_data or "tab" not in link_data:
        return None
    
    tab = link_data.get("tab")
    if tab not in ["suspicion", "pca", "changepoints", "clusters"]:
        return None
    
    # Extract context fields
    context = {}
    if "component" in link_data:
        context["component"] = link_data["component"]
    if "column" in link_data:
        context["column"] = link_data["column"]
    if "feature" in link_data:
        context["column"] = link_data["feature"]  # Normalize to 'column'
    if "cluster_id" in link_data:
        context["cluster_id"] = link_data["cluster_id"]
    if "target" in link_data:
        context["target"] = link_data["target"]
    
    return {"tab": tab, "context": context if context else None}


def render_navigation_breadcrumb() -> None:
    """Render a breadcrumb navigation bar showing current context.
    
    Displays current selection and provides a "Clear Filters" button.
    Typically called at the top of render_autotriage_results().
    """
    state = get_autotriage_state()
    breadcrumb = state.get_breadcrumb()
    
    if breadcrumb or state.last_navigation_source:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if breadcrumb:
                st.caption(f"🔍 {breadcrumb}")
            if state.last_navigation_source:
                st.caption(f"← Navigated from: {state.last_navigation_source.title()}")
        
        with col2:
            if st.button("Clear Filters", type="secondary", use_container_width=True):
                clear_autotriage_selections()
                st.rerun()


__all__ = [
    "AutoTriageState",
    "TabName",
    "get_autotriage_state",
    "set_active_autotriage_tab",
    "clear_autotriage_selections",
    "get_navigation_from_link",
    "render_navigation_breadcrumb",
]
