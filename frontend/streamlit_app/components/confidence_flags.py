"""Confidence flag components for displaying quality indicators.

Provides badge styling and tooltips for confidence flags returned
from analysis results, with severity-based coloring and filtering.
"""

import streamlit as st
from typing import List, Dict, Any, Optional


def render_confidence_badge(
    flag: Dict[str, Any],
    key_suffix: str = ""
) -> None:
    """Render a single confidence flag as a styled badge with tooltip.
    
    Args:
        flag: Flag dictionary with keys:
            - code: str (unique identifier)
            - message: str (human-readable description)
            - severity: str ("warning" | "info" | "error")
        key_suffix: Optional suffix for unique key generation
    """
    code = flag.get("code", "UNKNOWN")
    message = flag.get("message", "No description available")
    severity = flag.get("severity", "info").lower()
    
    # Map severity to color and icon
    severity_config = {
        "error": {"color": "error", "icon": "🔴", "label": "Error"},
        "warning": {"color": "warning", "icon": "⚠️", "label": "Warning"},
        "info": {"color": "info", "icon": "ℹ️", "label": "Info"},
    }
    
    config = severity_config.get(severity, severity_config["info"])
    
    # Display badge with tooltip
    st.markdown(
        f'<span class="badge badge-{config["color"]}" title="{message}">'
        f'{config["icon"]} {code}'
        f'</span>',
        unsafe_allow_html=True,
        help=message
    )


def render_flag_summary(
    flags: List[Dict[str, Any]],
    title: str = "Quality Flags"
) -> None:
    """Render an aggregate summary of all flags.
    
    Args:
        flags: List of flag dictionaries
        title: Section title
    """
    if not flags:
        return
    
    st.subheader(title)
    
    # Count by severity
    severity_counts = {"error": 0, "warning": 0, "info": 0}
    for flag in flags:
        severity = flag.get("severity", "info").lower()
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    # Display counts
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if severity_counts["error"] > 0:
            st.metric(
                "🔴 Errors",
                severity_counts["error"],
                help="Critical issues requiring attention"
            )
    
    with col2:
        if severity_counts["warning"] > 0:
            st.metric(
                "⚠️ Warnings",
                severity_counts["warning"],
                help="Potential issues or limitations"
            )
    
    with col3:
        if severity_counts["info"] > 0:
            st.metric(
                "ℹ️ Info",
                severity_counts["info"],
                help="Informational notes"
            )
    
    # Display all flags in expander
    with st.expander("📋 View All Flags", expanded=False):
        for idx, flag in enumerate(flags):
            render_confidence_badge(flag, key_suffix=f"_summary_{idx}")
            st.caption(flag.get("message", ""))
            if idx < len(flags) - 1:
                st.markdown("---")


def filter_by_severity(
    flags: List[Dict[str, Any]],
    selected_severities: List[str]
) -> List[Dict[str, Any]]:
    """Filter flags by severity level.
    
    Args:
        flags: List of flag dictionaries
        selected_severities: List of severity strings to include
        
    Returns:
        Filtered list of flags
    """
    if not selected_severities:
        return flags
    
    return [
        flag for flag in flags
        if flag.get("severity", "info").lower() in [s.lower() for s in selected_severities]
    ]


def render_flag_filter(
    flags: List[Dict[str, Any]],
    key: str = "flag_filter"
) -> List[str]:
    """Render a filter widget for selecting flag severities.
    
    Args:
        flags: List of all available flags
        key: Unique key for the widget
        
    Returns:
        List of selected severity levels
    """
    # Extract available severities
    available_severities = list(set(
        flag.get("severity", "info").lower()
        for flag in flags
    ))
    
    if not available_severities:
        return []
    
    # Create filter widget
    selected = st.multiselect(
        "Filter by severity",
        options=sorted(available_severities),
        default=sorted(available_severities),
        key=key,
        help="Select which severity levels to display"
    )
    
    return selected


def render_flags_inline(
    flags: List[Dict[str, Any]],
    max_display: int = 3
) -> None:
    """Render flags inline with limited display.
    
    Args:
        flags: List of flag dictionaries
        max_display: Maximum number of flags to show inline
    """
    if not flags:
        return
    
    # Display first N flags
    displayed_flags = flags[:max_display]
    remaining = len(flags) - max_display
    
    cols = st.columns(max_display + (1 if remaining > 0 else 0))
    
    for idx, flag in enumerate(displayed_flags):
        with cols[idx]:
            render_confidence_badge(flag, key_suffix=f"_inline_{idx}")
    
    if remaining > 0:
        with cols[-1]:
            st.caption(f"+{remaining} more")


def extract_flags_from_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all quality flags from an analysis result.
    
    Args:
        result: Analysis result dictionary
        
    Returns:
        Consolidated list of all flags from all result components
    """
    all_flags: List[Dict[str, Any]] = []
    
    # Top-level flags
    if "quality_flags" in result:
        all_flags.extend(result["quality_flags"])
    
    # Correlation table flags
    if "correlation_table" in result:
        table = result["correlation_table"]
        if "quality_flags" in table:
            all_flags.extend(table["quality_flags"])
        
        # Per-record flags
        for record in table.get("records", []):
            if "quality_flags" in record:
                all_flags.extend(record["quality_flags"])
    
    # Multivariate summary flags
    if "multivariate_summary" in result:
        summary = result["multivariate_summary"]
        if "quality_flags" in summary:
            all_flags.extend(summary["quality_flags"])
        
        # Per-model flags
        for model in summary.get("models", []):
            if "quality_flags" in model:
                all_flags.extend(model["quality_flags"])
    
    # Auto-triage flags
    if "auto_triage_result" in result:
        triage = result["auto_triage_result"]
        if "quality_flags" in triage:
            all_flags.extend(triage["quality_flags"])
        
        # Per-ranking flags
        for ranking in triage.get("suspicion_rankings", []):
            if "quality_flags" in ranking:
                all_flags.extend(ranking["quality_flags"])
    
    # AI summary flags
    if "ai_summary" in result and result["ai_summary"]:
        if "quality_flags" in result["ai_summary"]:
            all_flags.extend(result["ai_summary"]["quality_flags"])
    
    # Ranked insights flags
    for insight in result.get("ranked_insights", []):
        if "quality_flags" in insight:
            all_flags.extend(insight["quality_flags"])
    
    return all_flags
