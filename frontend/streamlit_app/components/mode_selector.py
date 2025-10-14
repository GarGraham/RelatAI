"""Mode selector component for analysis configuration.

Provides mode selection (Correlation, Multivariate, Auto-Triage) with
mode-specific parameter controls.
"""

import streamlit as st
from typing import Dict, Any, Literal

AnalysisMode = Literal["correlation", "multivariate", "auto_triage"]


def render_mode_selector(
    current_mode: str,
    current_params: Dict[str, Any],
    selected_columns: list[str]
) -> tuple[str, Dict[str, Any]]:
    """Render analysis mode selector with mode-specific parameters.
    
    Args:
        current_mode: Currently selected analysis mode
        current_params: Current parameter values
        selected_columns: List of selected columns (for validation)
        
    Returns:
        tuple: (selected_mode, parameters_dict)
    """
    st.subheader("🔬 Analysis Mode")
    
    # Mode selection with tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Correlation",
        "📈 Multivariate",
        "🔍 Auto-Triage"
    ])
    
    # Track which tab is active (workaround for Streamlit's tab state)
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = current_mode
    
    params = {}
    
    # Correlation Mode
    with tab1:
        if st.button("Select Correlation Mode", key="select_correlation", use_container_width=True):
            st.session_state.selected_mode = "correlation"
            st.rerun()
        
        _render_correlation_description()
        
        if st.session_state.selected_mode == "correlation":
            st.success("✅ Correlation mode active")
            params = _render_correlation_params(current_params)
    
    # Multivariate Mode
    with tab2:
        if st.button("Select Multivariate Mode", key="select_multivariate", use_container_width=True):
            st.session_state.selected_mode = "multivariate"
            st.rerun()
        
        _render_multivariate_description()
        
        if st.session_state.selected_mode == "multivariate":
            st.success("✅ Multivariate mode active")
            params = _render_multivariate_params(current_params, selected_columns)
    
    # Auto-Triage Mode
    with tab3:
        if st.button("Select Auto-Triage Mode", key="select_auto_triage", use_container_width=True):
            st.session_state.selected_mode = "auto_triage"
            st.rerun()
        
        _render_auto_triage_description()
        
        if st.session_state.selected_mode == "auto_triage":
            st.success("✅ Auto-Triage mode active")
            params = _render_auto_triage_params(current_params)
    
    return st.session_state.selected_mode, params


def _render_correlation_description():
    """Display description and guidance for Correlation mode."""
    st.markdown("""
    **Correlation Analysis** computes pairwise relationships between all selected variables.
    
    **Best For:**
    - Exploratory data analysis
    - Identifying related variables
    - No limit on number of variables
    
    **Methods Used:**
    - Numeric ↔ Numeric: Pearson, Spearman, Kendall
    - Categorical ↔ Categorical: Chi-square, Cramér's V
    - Mixed types: ANOVA, Point-Biserial
    """)


def _render_correlation_params(current_params: Dict[str, Any]) -> Dict[str, Any]:
    """Render parameters for Correlation mode.
    
    Args:
        current_params: Current parameter values
        
    Returns:
        Updated parameters dictionary
    """
    params = {}
    
    with st.expander("⚙️ Advanced Settings", expanded=False):
        params['correlation_threshold'] = st.slider(
            "Correlation Threshold",
            min_value=0.0,
            max_value=1.0,
            value=current_params.get('correlation_threshold', 0.1),
            step=0.05,
            help="Minimum absolute correlation to report"
        )
        
        params['p_value_threshold'] = st.slider(
            "P-value Threshold",
            min_value=0.001,
            max_value=0.10,
            value=current_params.get('p_value_threshold', 0.05),
            step=0.01,
            help="Maximum p-value for significance"
        )
        
        params['method_preference'] = st.selectbox(
            "Preferred Method (Numeric)",
            options=["pearson", "spearman", "kendall"],
            index=["pearson", "spearman", "kendall"].index(
                current_params.get('method_preference', 'pearson')
            ),
            help="Pearson: linear relationships | Spearman: monotonic | Kendall: rank-based"
        )
    
    return params


def _render_multivariate_description():
    """Display description and guidance for Multivariate mode."""
    st.markdown("""
    **Multivariate Analysis** builds regression models to understand relationships
    between anchor variables and predictors.
    
    **Best For:**
    - Understanding drivers of a specific outcome
    - Modeling with interactions
    - Limited to 3-5 variables for interpretability
    
    **Methods Used:**
    - Linear/Logistic Regression
    - ANOVA for categorical predictors
    - Partial Least Squares (PLS) for collinearity
    - Interaction term expansion
    """)


def _render_multivariate_params(
    current_params: Dict[str, Any],
    selected_columns: list[str]
) -> Dict[str, Any]:
    """Render parameters for Multivariate mode.
    
    Args:
        current_params: Current parameter values
        selected_columns: List of selected columns
        
    Returns:
        Updated parameters dictionary
    """
    params = {}
    
    # Max variables
    params['max_variables'] = st.number_input(
        "Maximum Variables",
        min_value=2,
        max_value=10,
        value=current_params.get('max_variables', 4),
        step=1,
        help="Maximum number of variables to include in any single model"
    )
    
    # Interaction depth
    params['interaction_depth'] = st.number_input(
        "Interaction Depth",
        min_value=1,
        max_value=3,
        value=current_params.get('interaction_depth', 2),
        step=1,
        help="Maximum order of interaction terms (1=no interactions, 2=pairwise, 3=three-way)"
    )
    
    # Include interactions toggle
    params['include_interactions'] = st.checkbox(
        "Include Interaction Terms",
        value=current_params.get('include_interactions', True),
        help="Generate and test interaction terms between predictors"
    )
    
    # Anchor columns selection info
    st.info(
        "💡 **Tip:** Select anchor columns in the Column Selection section above. "
        "Anchor columns are treated as response variables in regression models."
    )
    
    with st.expander("⚙️ Advanced Settings", expanded=False):
        params['use_pls'] = st.checkbox(
            "Use Partial Least Squares (PLS)",
            value=current_params.get('use_pls', False),
            help="Use PLS for highly correlated predictors"
        )
        
        params['vif_threshold'] = st.slider(
            "VIF Threshold (Multicollinearity)",
            min_value=1.0,
            max_value=10.0,
            value=current_params.get('vif_threshold', 5.0),
            step=0.5,
            help="Maximum Variance Inflation Factor before flagging collinearity"
        )
    
    return params


def _render_auto_triage_description():
    """Display description and guidance for Auto-Triage mode."""
    st.markdown("""
    **Auto-Triage Analysis** automatically identifies suspicious variables and patterns
    without requiring a specific outcome variable.
    
    **Best For:**
    - Quality event investigations
    - Root cause analysis
    - Anomaly detection
    - Unknown failure modes
    
    **Methods Used:**
    - PCA loadings (variance drivers)
    - Change-point detection (CUSUM, PELT)
    - Clustering (K-Means, Hierarchical)
    - Residual forensics
    - Suspicion ranking
    """)


def _render_auto_triage_params(current_params: Dict[str, Any]) -> Dict[str, Any]:
    """Render parameters for Auto-Triage mode.
    
    Args:
        current_params: Current parameter values
        
    Returns:
        Updated parameters dictionary
    """
    params = {}
    
    # PCA components
    params['n_components'] = st.slider(
        "PCA Components",
        min_value=2,
        max_value=10,
        value=current_params.get('n_components', 3),
        step=1,
        help="Number of principal components to compute"
    )
    
    # Clustering method
    params['clustering_method'] = st.selectbox(
        "Clustering Method",
        options=["kmeans", "hierarchical", "both"],
        index=["kmeans", "hierarchical", "both"].index(
            current_params.get('clustering_method', 'both')
        ),
        help="Algorithm for unsupervised grouping"
    )
    
    # Number of clusters
    params['n_clusters'] = st.slider(
        "Number of Clusters",
        min_value=2,
        max_value=10,
        value=current_params.get('n_clusters', 3),
        step=1,
        help="Target number of clusters (if not auto-detected)"
    )
    
    with st.expander("⚙️ Advanced Settings", expanded=False):
        # Change-point detection sensitivity
        params['changepoint_penalty'] = st.slider(
            "Change-Point Sensitivity",
            min_value=1,
            max_value=100,
            value=current_params.get('changepoint_penalty', 10),
            step=5,
            help="Lower = more sensitive to changes | Higher = fewer change points"
        )
        
        params['changepoint_method'] = st.selectbox(
            "Change-Point Algorithm",
            options=["cusum", "pelt", "both"],
            index=["cusum", "pelt", "both"].index(
                current_params.get('changepoint_method', 'both')
            ),
            help="CUSUM: cumulative sum | PELT: pruned exact linear time"
        )
        
        params['suspicion_threshold'] = st.slider(
            "Suspicion Threshold",
            min_value=0.0,
            max_value=1.0,
            value=current_params.get('suspicion_threshold', 0.7),
            step=0.05,
            help="Minimum suspicion score to flag a variable"
        )
    
    return params
