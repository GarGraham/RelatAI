"""Dataset upload page for RelatAI application.

This page handles file uploads, displays dataset profiles, and initiates
the analysis workflow.
"""

import io
from typing import Optional

import pandas as pd
import streamlit as st

from config import CONFIG
from utils import (
    APIError,
    debug_state,
    get_client,
    handle_api_error,
    initialize_session_state,
    load_dataset_context,
)

# -------------------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------------------

st.set_page_config(
    page_title=f"Upload Dataset - {CONFIG.page_title}",
    page_icon=CONFIG.page_icon,
    layout=CONFIG.layout,
)

# Initialize session state
initialize_session_state()

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------

def validate_file(file) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded file for size and format.
    
    Args:
        file: Streamlit UploadedFile object
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    file_size_mb = file.size / (1024 * 1024)
    if file_size_mb > CONFIG.max_upload_size_mb:
        return False, (
            f"File size ({file_size_mb:.1f} MB) exceeds maximum allowed "
            f"({CONFIG.max_upload_size_mb} MB). Please upload a smaller file."
        )
    
    # Check file extension
    file_ext = file.name.split('.')[-1].lower()
    if file_ext not in CONFIG.allowed_extensions:
        return False, (
            f"File type '.{file_ext}' is not supported. "
            f"Allowed types: {', '.join(CONFIG.allowed_extensions)}"
        )
    
    return True, None


def display_profile(profile: dict) -> None:
    """
    Display dataset profile information in a user-friendly format.
    
    Args:
        profile: Dataset profile dictionary from API
    """
    st.subheader("📋 Dataset Profile")
    
    # Overall statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows", f"{profile.get('row_count', 0):,}")
    with col2:
        st.metric("Total Columns", profile.get('column_count', 0))
    with col3:
        st.metric("Memory Size", f"{profile.get('memory_mb', 0):.2f} MB")
    
    st.markdown("---")
    
    # Column details
    st.subheader("Column Information")
    
    columns = profile.get('columns', [])
    if not columns:
        st.warning("No column information available")
        return
    
    # Group columns by type
    numeric_cols = [c for c in columns if c.get('logical_type') == 'numeric']
    categorical_cols = [c for c in columns if c.get('logical_type') == 'categorical']
    datetime_cols = [c for c in columns if c.get('logical_type') == 'datetime']
    text_cols = [c for c in columns if c.get('logical_type') == 'text']
    
    # Display counts
    col_counts = st.columns(4)
    with col_counts[0]:
        st.metric("Numeric", len(numeric_cols))
    with col_counts[1]:
        st.metric("Categorical", len(categorical_cols))
    with col_counts[2]:
        st.metric("DateTime", len(datetime_cols))
    with col_counts[3]:
        st.metric("Text", len(text_cols))
    
    # Detailed column table
    st.markdown("#### Column Details")
    
    # Create DataFrame for display
    column_data = []
    for col in columns:
        column_data.append({
            "Column": col.get('name', 'Unknown'),
            "Type": col.get('logical_type', 'Unknown'),
            "Missing %": f"{col.get('missing_percentage', 0):.1f}%",
            "Unique": col.get('unique_count', 0),
            "Stats": _format_column_stats(col),
        })
    
    df_columns = pd.DataFrame(column_data)
    st.dataframe(
        df_columns,
        use_container_width=True,
        hide_index=True,
    )
    
    # Quality warnings
    high_missing = [c for c in columns if c.get('missing_percentage', 0) > 50]
    if high_missing:
        st.warning(
            f"⚠️ {len(high_missing)} column(s) have >50% missing values: "
            f"{', '.join([c['name'] for c in high_missing[:5]])}"
            + ("..." if len(high_missing) > 5 else "")
        )


def _format_column_stats(column: dict) -> str:
    """Format column statistics for display."""
    logical_type = column.get('logical_type', '')
    
    if logical_type == 'numeric':
        stats = column.get('statistics', {})
        if stats:
            mean = stats.get('mean', 0)
            std = stats.get('std', 0)
            return f"μ={mean:.2f}, σ={std:.2f}"
    
    elif logical_type == 'categorical':
        unique = column.get('unique_count', 0)
        return f"{unique} categories"
    
    elif logical_type == 'datetime':
        stats = column.get('statistics', {})
        if stats and 'min' in stats and 'max' in stats:
            return f"{stats['min']} to {stats['max']}"
    
    return "-"


# -------------------------------------------------------------------------
# Main Content
# -------------------------------------------------------------------------

st.title("📊 Upload Dataset")

st.markdown("""
Upload your dataset to begin statistical analysis. RelatAI supports CSV, Excel, 
and Parquet file formats up to {max_mb} MB.
""".format(max_mb=CONFIG.max_upload_size_mb))

st.markdown("---")

# File upload widget
uploaded_file = st.file_uploader(
    "Choose a file",
    type=list(CONFIG.allowed_extensions),
    help=f"Maximum file size: {CONFIG.max_upload_size_mb} MB",
    key="file_uploader",
)

if uploaded_file is not None:
    # Validate file
    is_valid, error_msg = validate_file(uploaded_file)
    
    if not is_valid:
        st.error(f"❌ {error_msg}")
        st.stop()
    
    # Display file info
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.success(f"✅ File selected: **{uploaded_file.name}** ({file_size_mb:.2f} MB)")
    
    # Upload button
    if st.button("🚀 Upload and Profile Dataset", type="primary", use_container_width=True):
        try:
            with st.spinner("Uploading and profiling dataset... This may take a moment."):
                # Get API client
                client = get_client()
                
                # Reset file pointer
                uploaded_file.seek(0)
                
                # Upload dataset
                result = client.upload_dataset(
                    file=io.BytesIO(uploaded_file.read()),
                    filename=uploaded_file.name
                )
                
                # Store in session state
                # Backend returns: {metadata: {dataset_id, name, ...}, profile: {...}}
                metadata = result.get('metadata', {})
                profile = result.get('profile', {})
                dataset_id = metadata.get('dataset_id')
                
                # Flatten metadata for easier access in other pages
                flattened_metadata = {
                    'dataset_id': dataset_id,
                    'filename': metadata.get('original_filename', metadata.get('name', 'Unknown')),
                    'row_count': metadata.get('row_count', 0),
                    'column_count': metadata.get('column_count', 0),
                    'file_size_bytes': metadata.get('file_size_bytes', 0),
                    'uploaded_at': metadata.get('uploaded_at'),
                }
                
                st.session_state.dataset_metadata = flattened_metadata
                st.session_state.dataset_profile = profile
                
                # Load dataset context
                load_dataset_context(dataset_id)
                
                st.success(f"✅ Dataset uploaded successfully!")
                st.balloons()
                
        except APIError as e:
            st.error("Failed to upload dataset")
            handle_api_error(e)
            st.stop()
        
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            if CONFIG.debug_mode:
                st.exception(e)
            st.stop()

# Display profile if dataset is loaded
if st.session_state.dataset_metadata is not None:
    st.markdown("---")
    
    # Display profile
    profile = st.session_state.dataset_profile
    if profile:
        display_profile(profile)
    
    st.markdown("---")
    
    # Next steps
    st.subheader("✨ Next Steps")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "⚙️ Configure Analysis",
            use_container_width=True,
            type="primary",
        ):
            st.switch_page("pages/2_⚙️_Configuration.py")
        st.caption("Select columns, apply filters, and choose analysis mode")
    
    with col2:
        if st.button(
            "🔬 Quick Analysis",
            use_container_width=True,
        ):
            # Set default configuration and go directly to analysis
            st.info("Quick analysis with default settings coming soon!")
        st.caption("Run analysis with default settings (all columns, correlation mode)")

else:
    # Show example/help when no file is uploaded
    st.markdown("---")
    
    with st.expander("📖 Supported File Formats"):
        st.markdown("""
        **CSV Files (.csv)**
        - Most common format for tabular data
        - Can be exported from Excel, databases, and most analysis tools
        - Automatically detects delimiter (comma, tab, semicolon)
        
        **Excel Files (.xlsx, .xls)**
        - Native Microsoft Excel format
        - Reads first sheet by default
        - Preserves column types and formatting
        
        **Parquet Files (.parquet)**
        - Columnar storage format
        - Highly efficient for large datasets
        - Preserves data types and metadata
        """)
    
    with st.expander("⚙️ What Happens During Upload?"):
        st.markdown("""
        1. **Validation:** File size and format are checked
        2. **Upload:** File is securely transferred to the backend
        3. **Profiling:** Dataset is analyzed for:
           - Column types (numeric, categorical, datetime)
           - Missing value percentages
           - Basic statistics (mean, std, min, max)
           - Unique value counts
        4. **Storage:** Dataset is stored temporarily for analysis
        5. **Ready:** You can now configure and run analysis
        """)
    
    with st.expander("🔒 Data Privacy"):
        st.markdown("""
        - All data processing happens locally or on your private server
        - No data is transmitted to external services by default
        - Uploaded datasets are stored temporarily and can be deleted
        - Audit trail tracks all preprocessing actions
        - AI summarization can be disabled or kept local
        """)

# Debug panel
if CONFIG.debug_mode:
    st.markdown("---")
    debug_state()

# Footer
st.markdown("---")
st.caption(f"RelatAI v1.0 | Backend: {CONFIG.backend_url}")
