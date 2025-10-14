"""Preview table component for configuration validation.

Displays a live preview of the dataset after applying configuration
filters, showing row/column counts and sample data.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any


def render_preview_table(
    preview_data: Optional[Dict[str, Any]],
    is_loading: bool = False
) -> None:
    """Render a live preview of filtered dataset.
    
    Args:
        preview_data: Preview response from API containing:
            - row_count: Total rows after filtering
            - columns: List of column names
            - preview: List of dictionaries (row data)
        is_loading: Whether preview is currently loading
    """
    st.subheader("👁️ Configuration Preview")
    
    if is_loading:
        with st.spinner("Loading preview..."):
            st.info("Fetching preview data from backend...")
        return
    
    if not preview_data:
        st.warning("No preview available. Upload a dataset and configure columns to see preview.")
        return
    
    # Extract preview components
    row_count = preview_data.get('row_count', 0)
    columns = preview_data.get('columns', [])
    preview_rows = preview_data.get('preview', [])
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Rows",
            f"{row_count:,}",
            help="Number of rows after applying filters"
        )
    
    with col2:
        st.metric(
            "Columns",
            len(columns),
            help="Number of selected columns"
        )
    
    with col3:
        preview_count = len(preview_rows)
        st.metric(
            "Preview Rows",
            preview_count,
            help="Number of rows shown in preview table"
        )
    
    # Display preview data
    if not preview_rows:
        st.info("No data available with current filters.")
        return
    
    st.markdown("---")
    
    # Convert to DataFrame for display
    try:
        df_preview = pd.DataFrame(preview_rows)
        
        # Display with formatting
        st.dataframe(
            df_preview,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Quick statistics
        with st.expander("📊 Quick Statistics", expanded=False):
            _render_quick_stats(df_preview)
        
        # Column info
        with st.expander("📋 Column Information", expanded=False):
            _render_column_info(df_preview)
    
    except Exception as e:
        st.error(f"Error displaying preview: {str(e)}")


def _render_quick_stats(df: pd.DataFrame) -> None:
    """Render quick statistics for numeric columns in preview.
    
    Args:
        df: Preview dataframe
    """
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if not numeric_cols:
        st.info("No numeric columns in preview.")
        return
    
    st.markdown("**Numeric Column Statistics**")
    
    stats_df = df[numeric_cols].describe().T
    stats_df = stats_df.round(2)
    
    st.dataframe(
        stats_df,
        use_container_width=True
    )


def _render_column_info(df: pd.DataFrame) -> None:
    """Render column information including types and null counts.
    
    Args:
        df: Preview dataframe
    """
    st.markdown("**Column Details**")
    
    # Build column info table
    column_info = []
    for col in df.columns:
        info = {
            'Column': col,
            'Type': str(df[col].dtype),
            'Non-Null': df[col].count(),
            'Null': df[col].isna().sum(),
            'Unique': df[col].nunique()
        }
        column_info.append(info)
    
    info_df = pd.DataFrame(column_info)
    
    st.dataframe(
        info_df,
        use_container_width=True,
        hide_index=True
    )


def render_refresh_button(on_click_callback=None) -> bool:
    """Render a refresh button for the preview.
    
    Args:
        on_click_callback: Optional callback function to execute on click
        
    Returns:
        True if button was clicked
    """
    clicked = st.button(
        "🔄 Refresh Preview",
        use_container_width=True,
        help="Reload preview with current configuration"
    )
    
    if clicked and on_click_callback:
        on_click_callback()
    
    return clicked
