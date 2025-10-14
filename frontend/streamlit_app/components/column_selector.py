"""Column selector component for dataset configuration.

Provides a multi-select interface with search, filtering by data type,
and the ability to designate anchor columns for multivariate analysis.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional


def render_column_selector(
    all_columns: List[str],
    column_stats: Dict[str, Dict[str, Any]],
    selected_columns: List[str],
    anchor_columns: List[str] = None,
    show_anchors: bool = False
) -> tuple[List[str], List[str]]:
    """Render an interactive column selector with search and filtering.
    
    Args:
        all_columns: Complete list of available columns
        column_stats: Dictionary mapping column names to their statistics
            Expected keys: 'dtype', 'non_null_count', 'unique_count', 'mean', 'min', 'max'
        selected_columns: Currently selected columns
        anchor_columns: Currently selected anchor columns (for multivariate mode)
        show_anchors: Whether to show anchor column selection
        
    Returns:
        tuple: (selected_columns, anchor_columns)
    """
    if anchor_columns is None:
        anchor_columns = []
    
    st.subheader("📊 Column Selection")
    
    # Search and filter controls
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Search columns",
            placeholder="Type to filter columns...",
            key="column_search"
        )
    
    with col2:
        dtype_filter = st.multiselect(
            "Filter by type",
            options=["numeric", "categorical", "datetime", "text"],
            default=[],
            key="dtype_filter"
        )
    
    # Filter columns based on search and type
    filtered_columns = _filter_columns(all_columns, column_stats, search_term, dtype_filter)
    
    # Quick actions
    col_actions1, col_actions2, col_actions3 = st.columns(3)
    
    with col_actions1:
        if st.button("✅ Select All", use_container_width=True):
            selected_columns = filtered_columns.copy()
            st.rerun()
    
    with col_actions2:
        if st.button("❌ Clear All", use_container_width=True):
            selected_columns = []
            anchor_columns = []
            st.rerun()
    
    with col_actions3:
        if st.button("🔄 Select Numeric Only", use_container_width=True):
            selected_columns = [
                col for col in filtered_columns
                if column_stats.get(col, {}).get('dtype') == 'numeric'
            ]
            st.rerun()
    
    # Group columns by data type
    grouped_columns = _group_columns_by_type(filtered_columns, column_stats)
    
    # Display column selection with grouping
    st.markdown("---")
    st.markdown(f"**Showing {len(filtered_columns)} of {len(all_columns)} columns**")
    
    new_selected = []
    new_anchors = anchor_columns.copy() if show_anchors else []
    
    for dtype, columns in grouped_columns.items():
        if not columns:
            continue
            
        with st.expander(f"📁 {dtype.title()} ({len(columns)} columns)", expanded=True):
            # Show columns in this group
            for col in columns:
                col_container = st.container()
                
                with col_container:
                    col_check, col_name, col_anchor = st.columns([1, 6, 2])
                    
                    with col_check:
                        is_selected = st.checkbox(
                            "Select",
                            value=col in selected_columns,
                            key=f"select_{col}_{dtype}",
                            label_visibility="collapsed"
                        )
                        if is_selected:
                            new_selected.append(col)
                    
                    with col_name:
                        # Display column name with hover stats
                        stats = column_stats.get(col, {})
                        tooltip = _format_column_tooltip(col, stats)
                        st.markdown(
                            f"**{col}**  \n<small>{tooltip}</small>",
                            help=tooltip,
                            unsafe_allow_html=True
                        )
                    
                    with col_anchor:
                        if show_anchors and is_selected and dtype in ["numeric", "categorical"]:
                            is_anchor = st.checkbox(
                                "Anchor",
                                value=col in anchor_columns,
                                key=f"anchor_{col}_{dtype}",
                                help="Use as response variable in multivariate analysis"
                            )
                            if is_anchor and col not in new_anchors:
                                new_anchors.append(col)
                            elif not is_anchor and col in new_anchors:
                                new_anchors.remove(col)
    
    # Summary
    st.markdown("---")
    summary_col1, summary_col2 = st.columns(2)
    
    with summary_col1:
        st.metric("Selected Columns", len(new_selected))
    
    with summary_col2:
        if show_anchors:
            st.metric("Anchor Columns", len(new_anchors))
    
    return new_selected, new_anchors


def _filter_columns(
    columns: List[str],
    column_stats: Dict[str, Dict[str, Any]],
    search_term: str,
    dtype_filter: List[str]
) -> List[str]:
    """Filter columns based on search term and data type filter.
    
    Args:
        columns: List of column names to filter
        column_stats: Statistics for each column
        search_term: Search string to match against column names
        dtype_filter: List of data types to include
        
    Returns:
        Filtered list of column names
    """
    filtered = columns
    
    # Apply search filter
    if search_term:
        search_lower = search_term.lower()
        filtered = [col for col in filtered if search_lower in col.lower()]
    
    # Apply dtype filter
    if dtype_filter:
        filtered = [
            col for col in filtered
            if column_stats.get(col, {}).get('dtype') in dtype_filter
        ]
    
    return filtered


def _group_columns_by_type(
    columns: List[str],
    column_stats: Dict[str, Dict[str, Any]]
) -> Dict[str, List[str]]:
    """Group columns by their data type.
    
    Args:
        columns: List of column names
        column_stats: Statistics for each column
        
    Returns:
        Dictionary mapping data types to lists of column names
    """
    groups: Dict[str, List[str]] = {
        'numeric': [],
        'categorical': [],
        'datetime': [],
        'text': []
    }
    
    for col in columns:
        dtype = column_stats.get(col, {}).get('dtype', 'text')
        if dtype in groups:
            groups[dtype].append(col)
        else:
            groups['text'].append(col)
    
    return groups


def _format_column_tooltip(col: str, stats: Dict[str, Any]) -> str:
    """Format column statistics as a tooltip string.
    
    Args:
        col: Column name
        stats: Dictionary of column statistics
        
    Returns:
        Formatted tooltip string
    """
    dtype = stats.get('dtype', 'unknown')
    non_null = stats.get('non_null_count', 0)
    unique = stats.get('unique_count', 0)
    
    parts = [f"Type: {dtype}"]
    
    if non_null:
        parts.append(f"Non-null: {non_null:,}")
    
    if unique:
        parts.append(f"Unique: {unique:,}")
    
    # Add numeric-specific stats
    if dtype == 'numeric':
        if 'mean' in stats:
            parts.append(f"Mean: {stats['mean']:.2f}")
        if 'min' in stats and 'max' in stats:
            parts.append(f"Range: [{stats['min']:.2f}, {stats['max']:.2f}]")
    
    return " | ".join(parts)
