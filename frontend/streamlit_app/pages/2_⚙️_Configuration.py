"""Configuration page for dataset analysis setup.

Allows users to:
- Select columns to include in analysis
- Apply filters to subset data
- Choose analysis mode with parameters
- Preview filtered dataset
- Save/load configuration templates
"""

import streamlit as st
from typing import Optional
import traceback

from config import CONFIG
from utils import get_client, handle_api_error, initialize_session_state, get_state, set_state
from components import (
    render_column_selector,
    render_filter_panel,
    render_mode_selector,
    render_preview_table,
    render_refresh_button
)


# Page configuration
st.set_page_config(
    page_title="Configuration - RelatAI",
    page_icon="⚙️",
    layout="wide"
)

# Initialize session state
initialize_session_state()

# Load custom CSS
try:
    with open("assets/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass


def main():
    """Main configuration page logic."""
    st.title("⚙️ Analysis Configuration")
    
    # Check if dataset is loaded
    dataset_id = get_state('current_dataset_id')
    if not dataset_id:
        st.warning("⚠️ No dataset loaded. Please upload a dataset first.")
        if st.button("📊 Go to Upload Page"):
            st.switch_page("pages/1_📊_Dataset_Upload.py")
        return
    
    # Display current dataset info
    dataset_metadata = get_state('dataset_metadata', {})
    with st.sidebar:
        st.subheader("📊 Current Dataset")
        st.write(f"**Name:** {dataset_metadata.get('filename', 'Unknown')}")
        st.write(f"**Rows:** {dataset_metadata.get('row_count', 0):,}")
        st.write(f"**Columns:** {dataset_metadata.get('column_count', 0)}")
        st.markdown("---")
    
    # Get API client
    try:
        client = get_client()
    except Exception as e:
        st.error(f"❌ Failed to connect to backend: {str(e)}")
        return
    
    # Load or initialize configuration
    try:
        configuration = _load_configuration(client, dataset_id)
    except Exception as e:
        st.error(f"❌ Failed to load configuration: {str(e)}")
        handle_api_error(e)
        return
    
    # Extract configuration components
    all_columns = _get_all_columns()
    column_stats = _get_column_stats()
    selected_columns = configuration.get('selected_columns', [])
    anchor_columns = configuration.get('anchor_columns', [])
    filters = configuration.get('filters', {})
    analysis_mode = configuration.get('analysis_mode', 'correlation')
    mode_params = _extract_mode_params(configuration)
    
    # Layout with columns
    col_main, col_sidebar = st.columns([2, 1])
    
    with col_main:
        # Column Selector
        st.markdown("## 1️⃣ Select Columns")
        show_anchors = analysis_mode == "multivariate"
        new_selected, new_anchors = render_column_selector(
            all_columns=all_columns,
            column_stats=column_stats,
            selected_columns=selected_columns,
            anchor_columns=anchor_columns,
            show_anchors=show_anchors
        )
        
        st.markdown("---")
        
        # Filter Panel
        st.markdown("## 2️⃣ Apply Filters")
        preview_data_df = _get_preview_dataframe()
        new_filters = render_filter_panel(
            available_columns=new_selected if new_selected else all_columns,
            column_stats=column_stats,
            current_filters=filters,
            preview_data=preview_data_df
        )
        
        st.markdown("---")
        
        # Mode Selector
        st.markdown("## 3️⃣ Choose Analysis Mode")
        new_mode, new_params = render_mode_selector(
            current_mode=analysis_mode,
            current_params=mode_params,
            selected_columns=new_selected
        )
        
        st.markdown("---")
        
        # Advanced Settings (Collapsible)
        with st.expander("⚙️ Advanced Settings", expanded=False):
            st.markdown("### Preprocessing Controls")
            
            col_prep1, col_prep2 = st.columns(2)
            
            with col_prep1:
                st.markdown("**Missing Data Handling:**")
                imputation_strategy = st.selectbox(
                    "Imputation Strategy",
                    options=["mean", "median", "mode", "forward_fill", "backward_fill", "drop"],
                    index=1,  # median default
                    help="Method for handling missing values. Mean/median for numeric, mode for categorical.",
                    key="advanced_imputation"
                )
                
                st.markdown("**Outlier Handling:**")
                outlier_method = st.selectbox(
                    "Outlier Detection Method",
                    options=["iqr", "z_score", "isolation_forest", "none"],
                    index=0,  # IQR default
                    help="Method for detecting outliers. IQR: values beyond 1.5*IQR. Z-score: |z| > 3.",
                    key="advanced_outlier_method"
                )
                
                if outlier_method != "none":
                    outlier_action = st.radio(
                        "Outlier Action",
                        options=["clip", "remove", "flag_only"],
                        index=0,  # clip default
                        help="Clip: cap to threshold. Remove: delete rows. Flag: mark but keep.",
                        key="advanced_outlier_action"
                    )
                else:
                    outlier_action = "none"
            
            with col_prep2:
                st.markdown("**Scaling/Normalization:**")
                scaling_method = st.selectbox(
                    "Scaling Method",
                    options=["none", "standard", "minmax", "robust", "log"],
                    index=0,  # none default
                    help="Standard: (x-μ)/σ. MinMax: [0,1]. Robust: uses median/IQR. Log: log transform.",
                    key="advanced_scaling"
                )
                
                st.markdown("**Transformation:**")
                apply_transform = st.checkbox(
                    "Apply Power Transform",
                    value=False,
                    help="Apply Box-Cox or Yeo-Johnson transformation to achieve normality",
                    key="advanced_power_transform"
                )
                
                if apply_transform:
                    transform_method = st.radio(
                        "Transform Method",
                        options=["box-cox", "yeo-johnson"],
                        index=1,  # yeo-johnson (works with negative values)
                        help="Box-Cox: requires positive values. Yeo-Johnson: works with any values.",
                        key="advanced_transform_method"
                    )
                else:
                    transform_method = "none"
            
            st.markdown("---")
            st.markdown("### Performance Settings")
            
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                st.markdown("**Sampling:**")
                use_sampling = st.checkbox(
                    "Enable Data Sampling",
                    value=False,
                    help="Use subset of data for faster analysis. Recommended for datasets > 50k rows.",
                    key="advanced_sampling"
                )
                
                if use_sampling:
                    sample_size = st.number_input(
                        "Sample Size",
                        min_value=1000,
                        max_value=100000,
                        value=10000,
                        step=1000,
                        help="Number of rows to sample for analysis",
                        key="advanced_sample_size"
                    )
                    
                    sample_method = st.radio(
                        "Sampling Method",
                        options=["random", "stratified"],
                        index=0,
                        help="Random: uniform random sampling. Stratified: maintain class proportions.",
                        key="advanced_sample_method"
                    )
                else:
                    sample_size = None
                    sample_method = "none"
            
            with col_perf2:
                st.markdown("**Computation:**")
                use_parallel = st.checkbox(
                    "Enable Parallel Processing",
                    value=True,
                    help="Use multiple CPU cores for faster computation",
                    key="advanced_parallel"
                )
                
                if use_parallel:
                    n_workers = st.slider(
                        "Number of Workers",
                        min_value=1,
                        max_value=8,
                        value=4,
                        help="Number of parallel workers. More workers = faster but more memory.",
                        key="advanced_workers"
                    )
                else:
                    n_workers = 1
                
                cache_results = st.checkbox(
                    "Cache Analysis Results",
                    value=True,
                    help="Store results for faster retrieval on repeat runs",
                    key="advanced_cache"
                )
            
            st.markdown("---")
            st.markdown("### Sensitivity Thresholds")
            
            col_sens1, col_sens2 = st.columns(2)
            
            with col_sens1:
                st.markdown("**Statistical Significance:**")
                alpha_level = st.slider(
                    "Alpha Level (α)",
                    min_value=0.001,
                    max_value=0.1,
                    value=0.05,
                    step=0.001,
                    format="%.3f",
                    help="Threshold for statistical significance. Common values: 0.05, 0.01, 0.001",
                    key="advanced_alpha"
                )
                
                st.markdown("**Correlation Threshold:**")
                corr_threshold = st.slider(
                    "Minimum |Correlation|",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.3,
                    step=0.05,
                    help="Minimum absolute correlation to report",
                    key="advanced_corr_threshold"
                )
            
            with col_sens2:
                st.markdown("**Effect Size:**")
                min_effect_size = st.selectbox(
                    "Minimum Effect Size",
                    options=["small", "medium", "large", "none"],
                    index=3,  # none default
                    help="Cohen's d thresholds: small=0.2, medium=0.5, large=0.8",
                    key="advanced_effect_size"
                )
                
                st.markdown("**Sample Size:**")
                min_sample_size = st.number_input(
                    "Minimum Sample Size",
                    min_value=10,
                    max_value=1000,
                    value=30,
                    step=10,
                    help="Minimum n for valid statistical inference",
                    key="advanced_min_n"
                )
            
            # Store advanced settings in configuration
            advanced_settings = {
                "preprocessing": {
                    "imputation_strategy": imputation_strategy,
                    "outlier_method": outlier_method,
                    "outlier_action": outlier_action,
                    "scaling_method": scaling_method,
                    "power_transform": transform_method if apply_transform else "none"
                },
                "performance": {
                    "use_sampling": use_sampling,
                    "sample_size": sample_size if use_sampling else None,
                    "sample_method": sample_method if use_sampling else "none",
                    "parallel": use_parallel,
                    "n_workers": n_workers if use_parallel else 1,
                    "cache_results": cache_results
                },
                "thresholds": {
                    "alpha": alpha_level,
                    "correlation_min": corr_threshold,
                    "effect_size_min": min_effect_size,
                    "sample_size_min": min_sample_size
                }
            }
            
            # Add to mode params
            if 'advanced' not in new_params:
                new_params['advanced'] = advanced_settings
    
    with col_sidebar:
        # Configuration Actions
        st.subheader("💾 Actions")
        
        # Apply configuration button
        if st.button("✅ Apply Configuration", use_container_width=True, type="primary"):
            success = _apply_configuration(
                client=client,
                dataset_id=dataset_id,
                selected_columns=new_selected,
                anchor_columns=new_anchors,
                filters=new_filters,
                analysis_mode=new_mode,
                mode_params=new_params
            )
            if success:
                st.success("✅ Configuration applied successfully!")
                st.rerun()
        
        st.markdown("---")
        
        # Template Management
        st.subheader("📋 Templates")
        _render_template_management(client, dataset_id, configuration)
        
        st.markdown("---")
        
        # Navigation
        st.subheader("🧭 Next Steps")
        if st.button("🔬 Run Analysis", use_container_width=True):
            st.info("Analysis page coming in Phase 3!")
            # st.switch_page("pages/3_🔬_Analysis.py")
        
        if st.button("📊 Back to Upload", use_container_width=True):
            st.switch_page("pages/1_📊_Dataset_Upload.py")
    
    # Preview Section (full width at bottom)
    st.markdown("---")
    st.markdown("## 4️⃣ Preview Filtered Data")
    
    # Refresh preview button
    col_refresh, col_spacer = st.columns([1, 3])
    with col_refresh:
        if render_refresh_button():
            _refresh_preview(client, dataset_id)
    
    # Display preview
    preview_data = get_state('preview_data')
    is_loading = get_state('preview_loading', False)
    render_preview_table(preview_data, is_loading)


def _load_configuration(client, dataset_id: str) -> dict:
    """Load configuration from backend or session state.
    
    Args:
        client: API client instance
        dataset_id: Dataset identifier
        
    Returns:
        Configuration dictionary
    """
    # Check session state first
    config = get_state('configuration')
    if config and config.get('dataset_id') == dataset_id:
        return config
    
    # Load from backend
    try:
        config = client.get_configuration(dataset_id)
        set_state('configuration', config)
        return config
    except Exception as e:
        st.warning(f"Could not load existing configuration: {str(e)}")
        # Return default configuration
        return {
            'dataset_id': dataset_id,
            'selected_columns': _get_all_columns(),
            'anchor_columns': [],
            'filters': {},
            'analysis_mode': 'correlation',
            'max_variables': 4,
            'interaction_depth': 2,
            'include_interactions': True
        }


def _get_all_columns() -> list[str]:
    """Get all available columns from dataset profile."""
    profile = get_state('dataset_profile', {})
    columns = profile.get('columns', [])
    return [col['name'] for col in columns]


def _get_column_stats() -> dict:
    """Get column statistics from dataset profile.
    
    Returns:
        Dictionary mapping column names to their statistics
    """
    profile = get_state('dataset_profile', {})
    columns = profile.get('columns', [])
    
    stats = {}
    for col in columns:
        stats[col['name']] = {
            'dtype': col.get('type', 'text'),
            'non_null_count': col.get('non_null_count', 0),
            'unique_count': col.get('unique_count', 0),
            'mean': col.get('mean'),
            'min': col.get('min'),
            'max': col.get('max'),
            'sample_values': col.get('sample_values', [])
        }
    
    return stats


def _get_preview_dataframe():
    """Get preview data as DataFrame for filter panel."""
    preview_data = get_state('preview_data')
    if not preview_data:
        return None
    
    import pandas as pd
    preview_rows = preview_data.get('preview', [])
    if preview_rows:
        return pd.DataFrame(preview_rows)
    return None


def _extract_mode_params(configuration: dict) -> dict:
    """Extract mode-specific parameters from configuration.
    
    Args:
        configuration: Full configuration dictionary
        
    Returns:
        Dictionary of mode-specific parameters
    """
    return {
        'max_variables': configuration.get('max_variables', 4),
        'interaction_depth': configuration.get('interaction_depth', 2),
        'include_interactions': configuration.get('include_interactions', True),
    }


def _apply_configuration(
    client,
    dataset_id: str,
    selected_columns: list[str],
    anchor_columns: list[str],
    filters: dict,
    analysis_mode: str,
    mode_params: dict
) -> bool:
    """Apply configuration to backend and update session state.
    
    Args:
        client: API client instance
        dataset_id: Dataset identifier
        selected_columns: List of selected column names
        anchor_columns: List of anchor column names
        filters: Filter dictionary
        analysis_mode: Selected analysis mode
        mode_params: Mode-specific parameters
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Build update payload
        payload = {
            'selected_columns': selected_columns,
            'anchor_columns': anchor_columns,
            'filters': filters if filters else {},
            'analysis_mode': analysis_mode,
            **mode_params
        }
        
        # Send to backend
        updated_config = client.update_configuration(dataset_id, payload)
        
        # Update session state
        set_state('configuration', updated_config)
        
        # Refresh preview
        _refresh_preview(client, dataset_id)
        
        return True
    
    except Exception as e:
        st.error(f"Failed to apply configuration: {str(e)}")
        handle_api_error(e)
        return False


def _refresh_preview(client, dataset_id: str):
    """Refresh the configuration preview from backend.
    
    Args:
        client: API client instance
        dataset_id: Dataset identifier
    """
    try:
        set_state('preview_loading', True)
        preview_data = client.preview_configuration(dataset_id, limit=CONFIG.preview_row_limit)
        set_state('preview_data', preview_data)
        set_state('preview_loading', False)
    except Exception as e:
        set_state('preview_loading', False)
        st.error(f"Failed to load preview: {str(e)}")
        handle_api_error(e)


def _render_template_management(client, dataset_id: str, current_config: dict):
    """Render template save/load/delete controls.
    
    Args:
        client: API client instance
        dataset_id: Dataset identifier
        current_config: Current configuration dictionary
    """
    # List available templates
    try:
        templates = client.list_templates(dataset_id)
    except Exception as e:
        st.error(f"Failed to load templates: {str(e)}")
        templates = []
    
    # Save current configuration as template
    with st.expander("💾 Save Template", expanded=False):
        template_name = st.text_input(
            "Template Name",
            key="template_name",
            placeholder="e.g., Quality Event Config"
        )
        
        template_description = st.text_area(
            "Description (optional)",
            key="template_description",
            placeholder="Describe when to use this configuration..."
        )
        
        if st.button("Save Configuration", use_container_width=True):
            if not template_name:
                st.error("Please provide a template name")
            else:
                try:
                    template = client.create_template(
                        dataset_id=dataset_id,
                        name=template_name,
                        description=template_description,
                        configuration=current_config
                    )
                    st.success(f"✅ Template '{template_name}' saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save template: {str(e)}")
                    handle_api_error(e)
    
    # Load existing template
    if templates:
        with st.expander("📂 Load Template", expanded=False):
            template_options = {t['name']: t for t in templates}
            selected_template_name = st.selectbox(
                "Select Template",
                options=list(template_options.keys()),
                key="template_selector"
            )
            
            if selected_template_name:
                template = template_options[selected_template_name]
                
                # Show template description
                if template.get('description'):
                    st.info(template['description'])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Apply", use_container_width=True):
                        try:
                            # Apply template configuration
                            applied_config = client.apply_template(dataset_id, template['name'])
                            set_state('configuration', applied_config)
                            st.success(f"✅ Template '{selected_template_name}' applied!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to apply template: {str(e)}")
                            handle_api_error(e)
                
                with col2:
                    if st.button("🗑️ Delete", use_container_width=True):
                        try:
                            client.delete_template(dataset_id, template['name'])
                            st.success(f"✅ Template '{selected_template_name}' deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete template: {str(e)}")
                            handle_api_error(e)
    else:
        st.info("No templates saved yet. Save your first template above!")


if __name__ == "__main__":
    main()
