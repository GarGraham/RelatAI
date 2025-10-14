"""Filter panel component for dataset configuration.

Provides a dynamic filter builder with type-aware inputs for
numeric ranges, categorical multi-select, and date ranges.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, date


def render_filter_panel(
    available_columns: List[str],
    column_stats: Dict[str, Dict[str, Any]],
    current_filters: Dict[str, List[Any]],
    preview_data: Optional[pd.DataFrame] = None
) -> Dict[str, List[Any]]:
    """Render an interactive filter panel with dynamic filter builder.
    
    Args:
        available_columns: List of columns available for filtering
        column_stats: Dictionary mapping column names to their statistics
        current_filters: Currently applied filters {column_name: [values]}
        preview_data: Optional dataframe for extracting unique values
        
    Returns:
        Updated filters dictionary
    """
    st.subheader("🔍 Data Filters")
    
    # Initialize filters in session state if not present
    if 'filter_builder' not in st.session_state:
        st.session_state.filter_builder = {col: vals for col, vals in current_filters.items()}
    
    filters = st.session_state.filter_builder
    
    # Add new filter controls
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Filter columns that don't already have filters
        available_for_new = [col for col in available_columns if col not in filters]
        
        if available_for_new:
            new_filter_column = st.selectbox(
                "Add filter for column",
                options=[""] + available_for_new,
                key="new_filter_column"
            )
        else:
            new_filter_column = None
            st.info("All columns already have filters applied")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        if new_filter_column and st.button("➕ Add Filter", use_container_width=True):
            # Initialize empty filter for the selected column
            filters[new_filter_column] = []
            st.rerun()
    
    # Clear all filters button
    if filters:
        if st.button("🗑️ Clear All Filters", use_container_width=True):
            st.session_state.filter_builder = {}
            st.rerun()
    
    # Display active filters
    if not filters:
        st.info("No filters applied. Click 'Add Filter' to subset your data.")
        return {}
    
    st.markdown("---")
    st.markdown("**Active Filters**")
    
    filters_to_remove = []
    updated_filters = {}
    
    for col_name in list(filters.keys()):
        stats = column_stats.get(col_name, {})
        dtype = stats.get('dtype', 'text')
        
        with st.expander(f"📌 {col_name} ({dtype})", expanded=True):
            # Remove filter button
            col_label, col_remove = st.columns([4, 1])
            
            with col_remove:
                if st.button("❌", key=f"remove_{col_name}", help="Remove this filter"):
                    filters_to_remove.append(col_name)
                    continue
            
            # Render type-specific filter input
            if dtype == 'numeric':
                filter_value = _render_numeric_filter(col_name, stats, filters.get(col_name, []))
            elif dtype == 'categorical':
                filter_value = _render_categorical_filter(col_name, stats, filters.get(col_name, []), preview_data)
            elif dtype == 'datetime':
                filter_value = _render_datetime_filter(col_name, stats, filters.get(col_name, []))
            else:
                filter_value = _render_text_filter(col_name, filters.get(col_name, []))
            
            if filter_value is not None and len(filter_value) > 0:
                updated_filters[col_name] = filter_value
    
    # Remove filters marked for deletion
    for col_name in filters_to_remove:
        if col_name in st.session_state.filter_builder:
            del st.session_state.filter_builder[col_name]
    
    if filters_to_remove:
        st.rerun()
    
    # Update session state
    st.session_state.filter_builder = updated_filters
    
    # Summary
    if updated_filters:
        st.markdown("---")
        st.markdown(f"**{len(updated_filters)} filter(s) active**")
        
        # Show impact on row count if preview data available
        if preview_data is not None:
            original_rows = len(preview_data)
            st.metric(
                "Filtered Rows",
                original_rows,
                help="Row count after applying filters"
            )
    
    return updated_filters


def _render_numeric_filter(
    col_name: str,
    stats: Dict[str, Any],
    current_value: List[Any]
) -> List[float]:
    """Render numeric range filter with slider.
    
    Args:
        col_name: Column name
        stats: Column statistics (min, max, mean)
        current_value: Current filter value [min, max]
        
    Returns:
        List with [min_value, max_value]
    """
    min_val = float(stats.get('min', 0))
    max_val = float(stats.get('max', 100))
    
    # Handle edge case where min == max
    if min_val == max_val:
        st.warning(f"Column '{col_name}' has constant value: {min_val}")
        return [min_val, max_val]
    
    # Set default range
    if current_value and len(current_value) == 2:
        default_range = (float(current_value[0]), float(current_value[1]))
    else:
        default_range = (min_val, max_val)
    
    # Slider for range selection
    range_values = st.slider(
        f"Select range for {col_name}",
        min_value=min_val,
        max_value=max_val,
        value=default_range,
        key=f"filter_range_{col_name}",
        help=f"Mean: {stats.get('mean', 'N/A')}"
    )
    
    # Show selected range
    st.caption(f"Selected: {range_values[0]:.2f} to {range_values[1]:.2f}")
    
    return [range_values[0], range_values[1]]


def _render_categorical_filter(
    col_name: str,
    stats: Dict[str, Any],
    current_value: List[Any],
    preview_data: Optional[pd.DataFrame]
) -> List[str]:
    """Render categorical multi-select filter.
    
    Args:
        col_name: Column name
        stats: Column statistics
        current_value: Currently selected values
        preview_data: Dataframe to extract unique values from
        
    Returns:
        List of selected category values
    """
    # Extract unique values
    if preview_data is not None and col_name in preview_data.columns:
        unique_values = sorted(preview_data[col_name].dropna().unique().tolist())
    else:
        # Fallback to sample values from stats if available
        unique_values = stats.get('sample_values', [])
    
    if not unique_values:
        st.warning(f"No unique values available for '{col_name}'")
        return []
    
    # Limit display for large cardinality
    if len(unique_values) > 100:
        st.info(f"⚠️ Column has {len(unique_values)} unique values. Showing search interface.")
        
        # Text input for searching/filtering
        search_term = st.text_input(
            f"Search values in {col_name}",
            key=f"filter_search_{col_name}"
        )
        
        if search_term:
            unique_values = [v for v in unique_values if search_term.lower() in str(v).lower()]
    
    # Multi-select for category selection
    selected_values = st.multiselect(
        f"Select values to include",
        options=unique_values,
        default=current_value if current_value else [],
        key=f"filter_multi_{col_name}",
        help=f"Select one or more values. Empty = include all."
    )
    
    return selected_values


def _render_datetime_filter(
    col_name: str,
    stats: Dict[str, Any],
    current_value: List[Any]
) -> List[str]:
    """Render datetime range filter.
    
    Args:
        col_name: Column name
        stats: Column statistics (min, max dates)
        current_value: Current filter value [start_date, end_date]
        
    Returns:
        List with [start_date_str, end_date_str] in ISO format
    """
    # Parse min/max dates
    try:
        min_date = pd.to_datetime(stats.get('min', '2020-01-01')).date()
        max_date = pd.to_datetime(stats.get('max', datetime.now())).date()
    except:
        min_date = date(2020, 1, 1)
        max_date = date.today()
    
    # Set default range
    if current_value and len(current_value) == 2:
        try:
            default_start = pd.to_datetime(current_value[0]).date()
            default_end = pd.to_datetime(current_value[1]).date()
        except:
            default_start = min_date
            default_end = max_date
    else:
        default_start = min_date
        default_end = max_date
    
    # Date input widgets
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "From",
            value=default_start,
            min_value=min_date,
            max_value=max_date,
            key=f"filter_start_{col_name}"
        )
    
    with col2:
        end_date = st.date_input(
            "To",
            value=default_end,
            min_value=min_date,
            max_value=max_date,
            key=f"filter_end_{col_name}"
        )
    
    # Validate range
    if start_date > end_date:
        st.error("Start date must be before end date")
        return []
    
    return [start_date.isoformat(), end_date.isoformat()]


def _render_text_filter(
    col_name: str,
    current_value: List[Any]
) -> List[str]:
    """Render text filter with keyword search.
    
    Args:
        col_name: Column name
        current_value: Current filter keywords
        
    Returns:
        List of keywords to filter by
    """
    st.info("Text column: Enter keywords separated by commas")
    
    keywords_input = st.text_input(
        f"Keywords for {col_name}",
        value=", ".join(current_value) if current_value else "",
        key=f"filter_text_{col_name}",
        help="Separate multiple keywords with commas. Rows matching ANY keyword will be included."
    )
    
    if keywords_input:
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
        return keywords
    
    return []
