"""Streamlit prototype entrypoint for RelatAI.

This is the main application page that serves as the dashboard and entry point
for the RelatAI statistical triage platform.
"""

import streamlit as st

from config import CONFIG
from utils import debug_state, get_client, handle_api_error, has_active_dataset, initialize_session_state

# -------------------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------------------

st.set_page_config(
    page_title=CONFIG.page_title,
    page_icon=CONFIG.page_icon,
    layout=CONFIG.layout,
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------------
# Initialize Session State
# -------------------------------------------------------------------------

initialize_session_state()

# -------------------------------------------------------------------------
# Sidebar Navigation
# -------------------------------------------------------------------------

with st.sidebar:
    st.title(f"{CONFIG.page_icon} {CONFIG.page_title}")
    st.markdown("---")
    
    # Display current dataset info if one is loaded
    if has_active_dataset():
        st.success("✅ Dataset Loaded")
        dataset_id = st.session_state.current_dataset_id
        metadata = st.session_state.dataset_metadata
        
        st.info(f"**{metadata.get('filename', 'Unknown')}**")
        st.caption(f"ID: {dataset_id[:8]}...")
        
        profile = st.session_state.dataset_profile
        if profile:
            st.metric("Rows", f"{profile.get('row_count', 0):,}")
            st.metric("Columns", profile.get('column_count', 0))
        
        st.markdown("---")
    else:
        st.info("ℹ️ No dataset loaded")
        st.caption("Upload a dataset to get started")
        st.markdown("---")
    
    # Navigation shortcuts
    st.subheader("Quick Actions")
    
    if st.button("📊 Upload New Dataset", use_container_width=True):
        st.switch_page("pages/1_📊_Dataset_Upload.py")
    
    if has_active_dataset():
        if st.button("⚙️ Configure Analysis", use_container_width=True):
            st.switch_page("pages/2_⚙️_Configuration.py")
        
        if st.button("🔬 Run Analysis", use_container_width=True):
            st.switch_page("pages/3_🔬_Analysis.py")
        
        if st.button("📋 Manage Templates", use_container_width=True):
            st.switch_page("pages/4_📋_Templates.py")
    
    st.markdown("---")
    
    # Backend status check
    st.caption("**Backend Status**")
    try:
        client = get_client()
        health = client.health_check()
        st.success("🟢 Connected")
        if CONFIG.debug_mode:
            st.caption(f"URL: {CONFIG.backend_url}")
    except Exception as e:
        st.error("🔴 Disconnected")
        st.caption("Backend unavailable")
        if CONFIG.debug_mode:
            st.caption(f"Error: {str(e)[:50]}...")

# -------------------------------------------------------------------------
# Main Content
# -------------------------------------------------------------------------

st.title("Welcome to RelatAI")

st.markdown("""
RelatAI is a self-service statistical triage platform designed to rapidly surface 
statistical drivers during quality events and CAPA investigations.

### Getting Started

1. **📊 Upload Dataset** - Upload CSV, Excel, or Parquet files
2. **⚙️ Configure** - Select columns, apply filters, choose analysis mode
3. **🔬 Analyze** - Execute correlation, multivariate, or auto-triage analysis
4. **📊 Interpret** - View ranked insights, visualizations, and AI summaries

Use the navigation in the sidebar or the buttons below to begin.
""")

# Quick start buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Upload Dataset", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📊_Dataset_Upload.py")

with col2:
    if has_active_dataset():
        if st.button("⚙️ Configure", use_container_width=True):
            st.switch_page("pages/2_⚙️_Configuration.py")
    else:
        st.button("⚙️ Configure", use_container_width=True, disabled=True)
        st.caption("Upload a dataset first")

with col3:
    if has_active_dataset():
        if st.button("🔬 Analyze", use_container_width=True):
            st.switch_page("pages/3_🔬_Analysis.py")
    else:
        st.button("🔬 Analyze", use_container_width=True, disabled=True)
        st.caption("Upload a dataset first")

# Recent datasets section (placeholder for future enhancement)
st.markdown("---")
st.subheader("Recent Datasets")

if has_active_dataset():
    dataset_id = st.session_state.current_dataset_id
    metadata = st.session_state.dataset_metadata
    profile = st.session_state.dataset_profile
    
    with st.container():
        st.markdown(f"**{metadata.get('filename', 'Unknown')}**")
        st.caption(f"Dataset ID: {dataset_id}")
        
        if profile:
            col_a, col_b = st.columns(2)
            col_a.metric("Rows", f"{profile.get('row_count', 0):,}")
            col_b.metric("Columns", profile.get('column_count', 0))
        
        if st.button("Open Dataset", key="open_recent"):
            st.switch_page("pages/2_⚙️_Configuration.py")
else:
    st.info("No recent datasets. Upload a dataset to get started!")

# Help section
st.markdown("---")
with st.expander("ℹ️ Need Help?"):
    st.markdown("""
    **Supported File Formats:**
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    - Parquet (.parquet)
    
    **Maximum File Size:** {max_mb} MB
    
    **Analysis Modes:**
    - **Correlation:** Pairwise relationships across all variables
    - **Multivariate:** Regression and ANOVA with interaction terms
    - **Auto-Triage:** Unsupervised anomaly detection and driver ranking
    
    **For More Information:**
    - Check the documentation in `/docs`
    - Contact support for technical issues
    """.format(max_mb=CONFIG.max_upload_size_mb))

# Debug panel (only in debug mode)
if CONFIG.debug_mode:
    st.markdown("---")
    debug_state()
