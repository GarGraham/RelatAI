"""Analysis Execution & Results Display page.

Allows users to trigger analysis execution on configured datasets
and view comprehensive results with mode-specific visualizations.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import RelatAIClient
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
        client = RelatAIClient()
        
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
    flags = extract_flags_from_result(results)
    
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
    
    # Extract the inner 'result' field which contains the actual analysis data
    result_data = results.get('result', results)
    
    if mode == "correlation":
        render_correlation_results(result_data)
    
    elif mode == "multivariate":
        render_multivariate_results(result_data)
    
    elif mode == "auto_triage" or mode == "auto-triage":
        # For auto-triage, extract the nested auto_triage_result object
        auto_triage_data = result_data.get('auto_triage_result', {})
        render_autotriage_results(auto_triage_data)
    
    else:
        st.warning(f"Visualization not available for mode: {mode}")
        st.json(results)
    
    # Export options
    st.divider()
    render_export_options(results, mode)


def render_export_options(results: dict, mode: str):
    """Render comprehensive export controls for results.
    
    Args:
        results: Analysis results dictionary
        mode: Analysis mode
    """
    from utils.export_utils import (
        export_results_json,
        export_correlation_csv,
        export_multivariate_csv,
        export_autotriage_csv,
        create_export_package,
        format_export_metadata
    )
    from datetime import datetime
    
    st.subheader("📥 Export Results")
    
    # Get dataset info for naming
    dataset = get_selected_dataset()
    dataset_name = dataset.get('name', 'dataset').replace('.', '_') if dataset else 'dataset'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export format tabs
    tab1, tab2, tab3 = st.tabs(["📄 Quick Export", "📦 Complete Package", "📋 Data Only"])
    
    with tab1:
        st.markdown("**Quick single-file exports:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export JSON
            json_data = export_results_json(results, mode)
            
            st.download_button(
                label="📥 JSON (Full Results)",
                data=json_data,
                file_name=f"{dataset_name}_{mode}_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            # Export CSV (mode-specific)
            csv_data = None
            csv_label = "📊 CSV"
            
            if mode == "correlation":
                csv_data = export_correlation_csv(results)
                csv_label = "📊 CSV (Correlations)"
            elif mode == "multivariate":
                csv_data = export_multivariate_csv(results)
                csv_label = "📊 CSV (Coefficients)"
            elif mode == "auto_triage" or mode == "auto-triage":
                csv_data = export_autotriage_csv(results)
                csv_label = "📊 CSV (Rankings)"
            
            if csv_data:
                st.download_button(
                    label=csv_label,
                    data=csv_data,
                    file_name=f"{dataset_name}_{mode}_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.button(csv_label, disabled=True, use_container_width=True)
                st.caption("No data available")
        
        with col3:
            # Export metadata
            config = get_current_config()
            metadata_text = format_export_metadata(
                dataset_id=dataset.get('id', 'unknown') if dataset else 'unknown',
                dataset_name=dataset_name,
                mode=mode,
                config=config
            )
            
            st.download_button(
                label="📝 Metadata (TXT)",
                data=metadata_text,
                file_name=f"{dataset_name}_{mode}_{timestamp}_metadata.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    with tab2:
        st.markdown("**Export complete analysis package:**")
        st.caption("Includes JSON results, CSV tables, and metadata")
        
        # Create export package
        package = create_export_package(results, mode, dataset_name)
        
        # Display package contents
        with st.expander("📦 Package Contents", expanded=False):
            for filename in package.keys():
                st.text(f"• {filename}")
        
        # Instructions for downloading multiple files
        st.info("💡 **Tip:** Download each file individually below:")
        
        for filename, content in package.items():
            file_ext = filename.split('.')[-1]
            mime_type = {
                'json': 'application/json',
                'csv': 'text/csv',
                'txt': 'text/plain'
            }.get(file_ext, 'text/plain')
            
            st.download_button(
                label=f"📥 {filename}",
                data=content,
                file_name=filename,
                mime=mime_type,
                key=f"export_{filename}"
            )
    
    with tab3:
        st.markdown("**Export raw data tables:**")
        st.caption("Data-only exports for external analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Mode-specific data export
            if mode == "correlation":
                table_data = export_correlation_csv(results)
                st.download_button(
                    label="📊 Correlation Table (CSV)",
                    data=table_data,
                    file_name=f"{dataset_name}_correlation_table_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            elif mode == "multivariate":
                table_data = export_multivariate_csv(results)
                st.download_button(
                    label="📊 Coefficient Table (CSV)",
                    data=table_data,
                    file_name=f"{dataset_name}_coefficients_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            elif mode == "auto_triage" or mode == "auto-triage":
                table_data = export_autotriage_csv(results)
                st.download_button(
                    label="📊 Suspicion Rankings (CSV)",
                    data=table_data,
                    file_name=f"{dataset_name}_rankings_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            # Raw JSON (unformatted)
            import json
            raw_json = json.dumps(results)
            
            st.download_button(
                label="📄 Raw JSON (Compact)",
                data=raw_json,
                file_name=f"{dataset_name}_{mode}_raw_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )
    
    st.divider()
    
    # Export tips
    with st.expander("💡 Export Tips & Best Practices"):
        st.markdown("""
        **File Format Guide:**
        - **JSON**: Best for re-importing into RelatAI or programmatic analysis
        - **CSV**: Best for Excel, statistical software, or manual review
        - **TXT Metadata**: Provides analysis configuration and timestamp details
        
        **Recommended Workflows:**
        1. **Quick Review**: Download CSV for immediate viewing in Excel
        2. **Full Archive**: Use Complete Package for comprehensive documentation
        3. **External Analysis**: Use Data Only exports for importing into R/Python
        4. **Audit Trail**: Always download metadata with your results
        
        **File Naming Convention:**
        `{dataset_name}_{analysis_mode}_{timestamp}.{ext}`
        
        **Storage Recommendations:**
        - Organize exports by project or date
        - Keep metadata files with corresponding data files
        - Use version control for analysis configurations
        """)


if __name__ == "__main__":
    main()
