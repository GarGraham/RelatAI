"""Audit Trail viewer page.

Displays comprehensive audit log of all preprocessing and analysis actions
with timeline view, filtering, and CSV export capabilities.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import RelatAIClient
from utils.session_state import get_selected_dataset
from utils.export_utils import export_audit_log_csv
from components.audit_viewer import (
    render_audit_timeline,
    render_audit_filters,
    render_audit_summary,
    filter_audit_entries
)
from datetime import datetime


# Page configuration
st.set_page_config(
    page_title="Audit Trail - RelatAI",
    page_icon="📋",
    layout="wide"
)

# Apply custom CSS
css_path = Path(__file__).parent.parent / "assets" / "styles.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    """Main audit trail page function."""
    st.title("📋 Audit Trail")
    st.markdown("View preprocessing and analysis history with detailed action logs")
    
    st.divider()
    
    # Scope selection
    col1, col2 = st.columns([3, 1])
    
    with col1:
        scope = st.radio(
            "Audit Log Scope",
            options=["Current Dataset", "All Datasets"],
            horizontal=True,
            key="audit_scope"
        )
    
    with col2:
        # Refresh button
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Fetch audit logs
    dataset = get_selected_dataset()
    
    try:
        client = RelatAIClient()
        
        if scope == "Current Dataset" and dataset:
            dataset_id = dataset.get('id')
            st.caption(f"**Showing audit log for:** `{dataset.get('name', dataset_id)}`")
            audit_entries = client.get_audit_logs(dataset_id=dataset_id)
        
        elif scope == "Current Dataset" and not dataset:
            st.warning("⚠️ No dataset selected. Please upload a dataset first.")
            st.page_link("pages/1_📊_Dataset_Upload.py", label="Go to Dataset Upload", icon="📊")
            return
        
        else:  # All Datasets
            st.caption("**Showing audit log for:** All datasets")
            audit_entries = client.get_audit_logs()
        
    except Exception as e:
        st.error(f"❌ Failed to fetch audit logs: {str(e)}")
        return
    
    if not audit_entries:
        st.info("📝 No audit entries found. Audit logs are created when datasets are processed.")
        return
    
    # Summary metrics
    render_audit_summary(audit_entries)
    
    st.divider()
    
    # Filters
    filters = render_audit_filters()
    
    # Apply filters
    filtered_entries = filter_audit_entries(
        audit_entries,
        dataset_filter=filters.get('dataset'),
        action_filter=filters.get('actions'),
        date_range=filters.get('date_range')
    )
    
    st.divider()
    
    # Display filtered count
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.markdown(f"**Showing {len(filtered_entries)} of {len(audit_entries)} entries**")
    
    with col2:
        if len(filtered_entries) != len(audit_entries):
            if st.button("🔄 Clear Filters"):
                # Clear filter state
                for key in ['audit_dataset_filter', 'audit_action_filter', 'audit_date_preset']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    
    with col3:
        # Export button
        csv_data = export_audit_log_csv(filtered_entries)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="📥 Export CSV",
            data=csv_data,
            file_name=f"audit_log_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    st.divider()
    
    # Timeline view options
    view_col1, view_col2 = st.columns([3, 1])
    
    with view_col1:
        st.markdown("### 📅 Timeline View")
    
    with view_col2:
        show_details = st.checkbox("Expand All Details", value=False)
    
    # Render timeline
    if filtered_entries:
        render_audit_timeline(filtered_entries, show_details=show_details)
    else:
        st.info("No entries match the current filters")
    
    # Help section
    st.divider()
    
    with st.expander("❓ Audit Trail Help"):
        st.markdown("""
        ### Understanding the Audit Trail
        
        **What is logged:**
        - Dataset uploads and processing
        - Preprocessing actions (imputation, outlier removal, scaling)
        - Configuration changes (column selection, filters)
        - Analysis executions
        - Template operations
        
        **Action Icons:**
        - 🔧 **Imputation**: Missing data filled
        - ✂️ **Outlier Removal**: Extreme values removed
        - 📏 **Scaling**: Data normalized/standardized
        - 🔄 **Transformation**: Mathematical transformations applied
        - 🔍 **Filter Application**: Row filtering applied
        - 📊 **Column Selection**: Columns included/excluded
        
        **Filters:**
        - **Dataset ID**: Filter by specific dataset (partial match supported)
        - **Action Types**: Show only selected action types
        - **Date Range**: Filter by time period
        
        **Impact Metrics:**
        - **Rows Affected**: Number of rows modified by action
        - **Columns Affected**: Number of columns modified
        - **Changes Made**: Total number of changes (cells modified)
        
        **Export:**
        - Download filtered audit log as CSV for external analysis
        - Includes all metadata and impact metrics
        - Timestamps in ISO format for sorting
        
        **Use Cases:**
        1. **Compliance**: Track all data modifications for regulatory compliance
        2. **Debugging**: Understand what preprocessing was applied
        3. **Reproducibility**: Document exact steps taken in analysis
        4. **Collaboration**: Share processing history with team members
        
        **Best Practices:**
        - Regular review audit logs before analysis
        - Export logs when sharing results
        - Use filters to focus on specific time periods or actions
        - Document reasons for preprocessing decisions externally
        """)


if __name__ == "__main__":
    main()
