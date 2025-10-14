"""Analysis Execution & Results Display page.

Allows users to trigger analysis execution on configured datasets
and view comprehensive results with mode-specific visualizations.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import APIClient
from utils.session_state import (
    get_selected_dataset,
    get_analysis_mode,
    get_current_config,
    set_analysis_results,
    get_analysis_results,
    set_analysis_running
)
from components.confidence_flags import (
    render_flag_summary,
    render_flag_filter,
    render_flags_inline,
    extract_flags_from_result
)
from components.correlation_view import render_correlation_results
from components.multivariate_view import render_multivariate_results
from components.autotriage_view import render_autotriage_results
from components.ai_summary import render_ai_summary
import time


# Page configuration
st.set_page_config(
    page_title="Analysis - RelatAI",
    page_icon="🔬",
    layout="wide"
)

# Apply custom CSS
css_path = Path(__file__).parent.parent / "assets" / "styles.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    """Main analysis page function."""
    st.title("🔬 Analysis Execution & Results")
    
    # Check prerequisites
    dataset = get_selected_dataset()
    
    if not dataset:
        st.warning("⚠️ No dataset selected. Please upload a dataset first.")
        st.page_link("pages/1_📊_Dataset_Upload.py", label="Go to Dataset Upload", icon="📊")
        return
    
    # Display dataset info
    st.markdown(f"**Dataset:** `{dataset.get('name', 'Unknown')}`")
    st.markdown(f"**ID:** `{dataset.get('id', 'Unknown')}`")
    
    st.divider()
    
    # Analysis mode selection
    mode = get_analysis_mode()
    
    if not mode:
        st.warning("⚠️ No analysis mode configured. Please configure your analysis.")
        st.page_link("pages/2_⚙️_Configuration.py", label="Go to Configuration", icon="⚙️")
        return
    
    st.markdown(f"**Analysis Mode:** `{mode}`")
    
    # Check for existing results
    existing_results = get_analysis_results()
    has_results = existing_results is not None
    
    # Analysis execution section
    st.subheader("Run Analysis")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Configuration preview
        config = get_current_config()
        
        if config:
            with st.expander("📋 Current Configuration", expanded=False):
                st.json(config)
    
    with col2:
        run_button = st.button(
            "▶️ Run Analysis",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get('analysis_running', False)
        )
    
    with col3:
        if has_results:
            clear_button = st.button(
                "🗑️ Clear Results",
                use_container_width=True
            )
            
            if clear_button:
                set_analysis_results(None)
                st.rerun()
    
    # Execute analysis
    if run_button:
        execute_analysis(dataset['id'], mode, config)
    
    # Display results if available
    if has_results:
        st.divider()
        display_results(existing_results, mode)


def execute_analysis(dataset_id: str, mode: str, config: dict):
    """Execute analysis and handle progress tracking.
    
    Args:
        dataset_id: Dataset identifier
        mode: Analysis mode
        config: Analysis configuration
    """
    # Set running state
    set_analysis_running(True)
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Initialize API client
        client = APIClient()
        
        # Start analysis
        status_text.text("🔄 Initiating analysis...")
        progress_bar.progress(10)
        time.sleep(0.5)
        
        # Call backend
        status_text.text(f"🔄 Running {mode} analysis...")
        progress_bar.progress(30)
        
        # Execute analysis
        result = client.run_analysis(
            dataset_id=dataset_id,
            mode=mode,
            parameters=config
        )
        
        progress_bar.progress(80)
        status_text.text("✅ Processing results...")
        time.sleep(0.5)
        
        # Store results
        set_analysis_results(result)
        
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        time.sleep(1)
        st.success(f"✅ {mode.capitalize()} analysis completed successfully!")
        
        # Check for cache hit
        if result.get('cache_hit'):
            st.info("ℹ️ Results retrieved from cache (previously computed)")
        
        time.sleep(1)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        st.exception(e)
    
    finally:
        # Clear running state
        set_analysis_running(False)


def display_results(results: dict, mode: str):
    """Display analysis results with mode-specific visualizations.
    
    Args:
        results: Analysis results dictionary
        mode: Analysis mode
    """
    st.subheader("Analysis Results")
    
    # Metadata
    col1, col2, col3 = st.columns(3)
    
    with col1:
        generated_at = results.get('generated_at', 'Unknown')
        st.caption(f"**Generated:** {generated_at}")
    
    with col2:
        cache_hit = results.get('cache_hit', False)
        cache_status = "From Cache" if cache_hit else "Fresh Computation"
        st.caption(f"**Status:** {cache_status}")
    
    with col3:
        exec_time = results.get('execution_time_seconds')
        if exec_time:
            st.caption(f"**Execution Time:** {exec_time:.2f}s")
    
    st.divider()
    
    # Extract and display confidence flags
    flags = extract_flags_from_result(results, mode)
    
    if flags:
        st.markdown("### ⚠️ Quality Indicators")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            render_flags_inline(flags, max_display=5)
        
        with col2:
            render_flag_summary(flags)
        
        st.divider()
    
    # AI Summary (collapsible)
    render_ai_summary(results, mode)
    
    st.divider()
    
    # Mode-specific visualizations
    st.markdown("### 📊 Detailed Results")
    
    if mode == "correlation":
        render_correlation_results(results)
    
    elif mode == "multivariate":
        render_multivariate_results(results)
    
    elif mode == "auto-triage":
        render_autotriage_results(results)
    
    else:
        st.warning(f"Visualization not available for mode: {mode}")
        st.json(results)
    
    # Export options
    st.divider()
    render_export_options(results, mode)


def render_export_options(results: dict, mode: str):
    """Render export controls for results.
    
    Args:
        results: Analysis results dictionary
        mode: Analysis mode
    """
    st.subheader("Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export JSON
        import json
        
        json_str = json.dumps(results, indent=2)
        
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"analysis_results_{mode}.json",
            mime="application/json"
        )
    
    with col2:
        # Export summary (placeholder for future CSV export)
        st.button("📊 Export Summary (CSV)", disabled=True)
        st.caption("Coming soon")
    
    with col3:
        # Export visualizations (placeholder)
        st.button("🖼️ Export Visualizations", disabled=True)
        st.caption("Coming soon")


if __name__ == "__main__":
    main()
