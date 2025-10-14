"""Audit trail viewer components for displaying preprocessing history.

Provides reusable components for displaying audit log entries with
timeline visualization, filtering, and detailed action inspection.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


def render_audit_timeline(
    audit_entries: List[Dict[str, Any]],
    show_details: bool = False
) -> None:
    """Render audit entries as a timeline.
    
    Args:
        audit_entries: List of audit log entry dictionaries
        show_details: Whether to show expanded details by default
    """
    if not audit_entries:
        st.info("No audit entries to display")
        return
    
    # Sort by timestamp (most recent first)
    sorted_entries = sorted(
        audit_entries,
        key=lambda x: x.get('timestamp', ''),
        reverse=True
    )
    
    for idx, entry in enumerate(sorted_entries):
        render_audit_entry(entry, idx, show_details)


def render_audit_entry(
    entry: Dict[str, Any],
    entry_id: int,
    expanded: bool = False
) -> None:
    """Render a single audit log entry with expandable details.
    
    Args:
        entry: Audit log entry dictionary
        entry_id: Unique identifier for the entry
        expanded: Whether to expand details by default
    """
    timestamp = entry.get('timestamp', 'Unknown')
    action = entry.get('action', 'Unknown Action')
    dataset_id = entry.get('dataset_id', 'Unknown')
    
    # Format timestamp
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        relative_time = get_relative_time(dt)
    except:
        time_str = timestamp
        relative_time = ""
    
    # Action icon
    action_icon = get_action_icon(action)
    
    # Entry header
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"### {action_icon} {action}")
            st.caption(f"🕒 {time_str} ({relative_time})")
        
        with col2:
            st.caption(f"**Dataset:**")
            st.caption(f"`{dataset_id[:12]}...`" if len(dataset_id) > 12 else f"`{dataset_id}`")
        
        # Expandable details
        with st.expander("📋 Details", expanded=expanded):
            # Details text
            details = entry.get('details', 'No details available')
            st.text(details)
            
            # Parameters
            if 'parameters' in entry and entry['parameters']:
                st.markdown("**Parameters:**")
                st.json(entry['parameters'])
            
            # Impact
            if 'impact' in entry and entry['impact']:
                impact = entry['impact']
                st.markdown("**Impact:**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    rows_affected = impact.get('rows_affected', 'N/A')
                    st.metric("Rows Affected", rows_affected)
                
                with col2:
                    cols_affected = impact.get('columns_affected', 'N/A')
                    st.metric("Columns Affected", cols_affected)
                
                with col3:
                    changes = impact.get('changes_made', 'N/A')
                    st.metric("Changes", changes)
            
            # User info
            if 'user' in entry and entry['user']:
                st.caption(f"**User:** {entry['user']}")
        
        st.divider()


def filter_audit_entries(
    entries: List[Dict[str, Any]],
    dataset_filter: Optional[str] = None,
    action_filter: Optional[List[str]] = None,
    date_range: Optional[tuple] = None
) -> List[Dict[str, Any]]:
    """Filter audit entries by various criteria.
    
    Args:
        entries: List of audit entries
        dataset_filter: Filter by dataset ID (partial match)
        action_filter: List of action types to include
        date_range: Tuple of (start_date, end_date) datetime objects
    
    Returns:
        Filtered list of audit entries
    """
    filtered = entries.copy()
    
    # Filter by dataset
    if dataset_filter:
        filtered = [
            e for e in filtered
            if dataset_filter.lower() in e.get('dataset_id', '').lower()
        ]
    
    # Filter by action
    if action_filter:
        filtered = [
            e for e in filtered
            if e.get('action') in action_filter
        ]
    
    # Filter by date range
    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = [
            e for e in filtered
            if is_within_date_range(e.get('timestamp', ''), start_date, end_date)
        ]
    
    return filtered


def render_audit_filters() -> Dict[str, Any]:
    """Render filter controls for audit log.
    
    Returns:
        Dictionary with filter values
    """
    st.markdown("### 🔍 Filters")
    
    col1, col2, col3 = st.columns(3)
    
    filters = {}
    
    with col1:
        # Dataset filter
        dataset_filter = st.text_input(
            "Dataset ID (partial match)",
            placeholder="Enter dataset ID...",
            key="audit_dataset_filter"
        )
        filters['dataset'] = dataset_filter if dataset_filter else None
    
    with col2:
        # Action filter
        available_actions = [
            "imputation",
            "outlier_removal",
            "scaling",
            "transformation",
            "filter_application",
            "column_selection"
        ]
        
        action_filter = st.multiselect(
            "Action Types",
            options=available_actions,
            key="audit_action_filter"
        )
        filters['actions'] = action_filter if action_filter else None
    
    with col3:
        # Date range filter
        date_preset = st.selectbox(
            "Date Range",
            options=["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Custom"],
            key="audit_date_preset"
        )
        
        if date_preset == "Custom":
            start_date = st.date_input("From", key="audit_start_date")
            end_date = st.date_input("To", key="audit_end_date")
            filters['date_range'] = (
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time())
            )
        elif date_preset == "Last 24 Hours":
            filters['date_range'] = (datetime.now() - timedelta(days=1), datetime.now())
        elif date_preset == "Last 7 Days":
            filters['date_range'] = (datetime.now() - timedelta(days=7), datetime.now())
        elif date_preset == "Last 30 Days":
            filters['date_range'] = (datetime.now() - timedelta(days=30), datetime.now())
        else:
            filters['date_range'] = None
    
    return filters


def render_audit_summary(entries: List[Dict[str, Any]]) -> None:
    """Render summary statistics for audit entries.
    
    Args:
        entries: List of audit entries
    """
    if not entries:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Entries", len(entries))
    
    with col2:
        unique_datasets = len(set(e.get('dataset_id', '') for e in entries))
        st.metric("Unique Datasets", unique_datasets)
    
    with col3:
        unique_actions = len(set(e.get('action', '') for e in entries))
        st.metric("Action Types", unique_actions)
    
    with col4:
        # Calculate time span
        timestamps = [e.get('timestamp', '') for e in entries if e.get('timestamp')]
        if timestamps:
            try:
                dates = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamps]
                time_span = (max(dates) - min(dates)).days
                st.metric("Time Span (days)", time_span)
            except:
                st.metric("Time Span", "N/A")
        else:
            st.metric("Time Span", "N/A")


def get_action_icon(action: str) -> str:
    """Get icon for action type.
    
    Args:
        action: Action type string
    
    Returns:
        Emoji icon
    """
    icon_map = {
        'imputation': '🔧',
        'outlier_removal': '✂️',
        'scaling': '📏',
        'transformation': '🔄',
        'filter_application': '🔍',
        'column_selection': '📊',
        'upload': '📤',
        'analysis': '🔬',
        'export': '📥'
    }
    
    return icon_map.get(action.lower(), '📋')


def get_relative_time(dt: datetime) -> str:
    """Get human-readable relative time.
    
    Args:
        dt: Datetime object
    
    Returns:
        Relative time string (e.g., "2 hours ago")
    """
    now = datetime.now(dt.tzinfo)
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def is_within_date_range(
    timestamp: str,
    start_date: datetime,
    end_date: datetime
) -> bool:
    """Check if timestamp is within date range.
    
    Args:
        timestamp: ISO format timestamp string
        start_date: Start of date range
        end_date: End of date range
    
    Returns:
        True if timestamp is within range
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        # Make start_date and end_date timezone-aware if needed
        if dt.tzinfo and not start_date.tzinfo:
            start_date = start_date.replace(tzinfo=dt.tzinfo)
        if dt.tzinfo and not end_date.tzinfo:
            end_date = end_date.replace(tzinfo=dt.tzinfo)
        return start_date <= dt <= end_date
    except:
        return False
