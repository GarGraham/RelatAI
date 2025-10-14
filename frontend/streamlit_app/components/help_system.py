"""Help system with contextual tooltips and documentation.

Provides reusable help components with statistical method descriptions,
interpretation guides, and best practices for analysis workflows.
"""

import streamlit as st
from typing import Optional, Dict, Any


# Statistical method descriptions
STATISTICAL_METHODS = {
    "pearson": {
        "name": "Pearson Correlation",
        "description": "Measures linear relationship between two continuous variables",
        "assumptions": [
            "Variables are continuous",
            "Linear relationship exists",
            "Bivariate normal distribution",
            "No significant outliers"
        ],
        "interpretation": "Range: [-1, 1]. ±1 = perfect linear relationship, 0 = no linear relationship",
        "when_to_use": "Use for continuous variables with linear relationships"
    },
    "spearman": {
        "name": "Spearman Correlation",
        "description": "Measures monotonic relationship based on ranked values",
        "assumptions": [
            "Variables are ordinal or continuous",
            "Monotonic relationship (not necessarily linear)"
        ],
        "interpretation": "Range: [-1, 1]. Robust to outliers and non-linear relationships",
        "when_to_use": "Use when data is not normally distributed or contains outliers"
    },
    "kendall": {
        "name": "Kendall's Tau",
        "description": "Measures concordance between rankings of two variables",
        "assumptions": [
            "Variables are ordinal or continuous",
            "Monotonic relationship"
        ],
        "interpretation": "Range: [-1, 1]. More robust than Spearman for small sample sizes",
        "when_to_use": "Use for small samples or when ties are present"
    },
    "regression": {
        "name": "Linear Regression",
        "description": "Models relationship between dependent variable and one or more predictors",
        "assumptions": [
            "Linear relationship exists",
            "Residuals are normally distributed",
            "Homoscedasticity (constant variance)",
            "Independence of observations",
            "No multicollinearity among predictors"
        ],
        "interpretation": "Coefficients indicate change in Y for unit change in X",
        "when_to_use": "Use to predict or explain continuous outcomes"
    },
    "anova": {
        "name": "Analysis of Variance (ANOVA)",
        "description": "Tests if means differ across groups",
        "assumptions": [
            "Dependent variable is continuous",
            "Independent variable is categorical",
            "Normal distribution within groups",
            "Homogeneity of variance across groups"
        ],
        "interpretation": "F-statistic tests if group means differ significantly",
        "when_to_use": "Use to compare means across 3+ groups"
    },
    "pca": {
        "name": "Principal Component Analysis (PCA)",
        "description": "Reduces dimensionality while preserving variance",
        "assumptions": [
            "Variables are continuous",
            "Linear relationships among variables",
            "Large sample size (n > variables)"
        ],
        "interpretation": "Components are orthogonal. First PC captures most variance",
        "when_to_use": "Use for dimensionality reduction or identifying patterns"
    },
    "changepoint": {
        "name": "Change-Point Detection",
        "description": "Identifies points where statistical properties change",
        "assumptions": [
            "Time-ordered or sequential data",
            "Changes occur at discrete points"
        ],
        "interpretation": "Detected points indicate regime shifts or structural breaks",
        "when_to_use": "Use to detect shifts in time series or sequential data"
    },
    "clustering": {
        "name": "Clustering Analysis",
        "description": "Groups similar observations without predefined labels",
        "assumptions": [
            "Variables are numeric",
            "Distance metric is meaningful",
            "Clusters are separable"
        ],
        "interpretation": "Silhouette score >0.5 indicates good separation",
        "when_to_use": "Use to discover natural groupings in data"
    }
}


# Interpretation guides
INTERPRETATION_GUIDES = {
    "correlation_strength": {
        "title": "Interpreting Correlation Strength",
        "content": """
        **Effect Size Guidelines (Cohen, 1988):**
        - **0.00 - 0.10**: Negligible correlation
        - **0.10 - 0.30**: Small/weak correlation
        - **0.30 - 0.50**: Moderate correlation
        - **0.50 - 0.70**: Large/strong correlation
        - **0.70 - 1.00**: Very strong correlation
        
        **Important Notes:**
        - Correlation ≠ causation
        - Consider sample size (large n can make small r significant)
        - Check scatter plot for linearity
        - Be aware of outliers' influence
        """
    },
    "p_values": {
        "title": "Understanding P-Values",
        "content": """
        **What is a p-value?**
        Probability of observing results as extreme as yours, assuming null hypothesis is true.
        
        **Common Thresholds:**
        - **p < 0.001**: Very strong evidence against null
        - **p < 0.01**: Strong evidence against null
        - **p < 0.05**: Moderate evidence against null (conventional cutoff)
        - **p > 0.05**: Insufficient evidence to reject null
        
        **Important Notes:**
        - P-values are NOT effect sizes
        - Statistical significance ≠ practical significance
        - Large samples can produce significant but trivial effects
        - Consider confidence intervals and effect sizes
        """
    },
    "r_squared": {
        "title": "Interpreting R² (Coefficient of Determination)",
        "content": """
        **What does R² mean?**
        Proportion of variance in dependent variable explained by model.
        
        **Guidelines:**
        - **R² < 0.3**: Weak explanatory power
        - **R² 0.3 - 0.5**: Moderate explanatory power
        - **R² 0.5 - 0.7**: Substantial explanatory power
        - **R² > 0.7**: Strong explanatory power
        
        **Important Notes:**
        - Higher R² isn't always better (overfitting risk)
        - Use adjusted R² for multiple predictors
        - Consider context (social sciences vs physical sciences)
        - Inspect residual plots for model fit
        """
    },
    "vif": {
        "title": "Variance Inflation Factor (VIF)",
        "content": """
        **What is VIF?**
        Measures how much variance of coefficient is inflated due to multicollinearity.
        
        **Interpretation:**
        - **VIF = 1**: No correlation with other predictors
        - **VIF 1-5**: Moderate correlation (acceptable)
        - **VIF 5-10**: High correlation (problematic)
        - **VIF > 10**: Severe multicollinearity (remove variable)
        
        **Solutions for High VIF:**
        - Remove highly correlated predictors
        - Combine correlated variables
        - Use regularization (Ridge/Lasso)
        - Apply PCA for dimensionality reduction
        """
    },
    "confidence_intervals": {
        "title": "Confidence Intervals",
        "content": """
        **What is a confidence interval?**
        Range of values likely to contain true population parameter.
        
        **95% Confidence Interval:**
        If we repeated the study 100 times, 95 intervals would contain the true value.
        
        **Interpretation:**
        - **Wider intervals**: More uncertainty (smaller sample, more variance)
        - **Narrower intervals**: More precision (larger sample, less variance)
        - **Does not contain zero**: Effect is statistically significant (at α=0.05)
        
        **Important Notes:**
        - 95% is conventional but not mandatory
        - CI provides more information than p-value alone
        - Consider practical significance, not just statistical
        """
    }
}


# Best practices
BEST_PRACTICES = {
    "data_quality": {
        "title": "Data Quality Best Practices",
        "practices": [
            "✓ Check for missing data patterns before imputation",
            "✓ Inspect outliers visually (not all outliers are errors)",
            "✓ Validate data types match analysis requirements",
            "✓ Document all preprocessing decisions",
            "✓ Keep original data unchanged (use copies)",
            "✓ Use appropriate imputation for data type",
            "✓ Consider domain knowledge when handling outliers"
        ]
    },
    "correlation_analysis": {
        "title": "Correlation Analysis Best Practices",
        "practices": [
            "✓ Visualize relationships with scatter plots first",
            "✓ Check for non-linear relationships (use Spearman/Kendall)",
            "✓ Look for outliers that may drive correlation",
            "✓ Consider sample size (small n = unreliable estimates)",
            "✓ Remember: correlation ≠ causation",
            "✓ Report effect size (r) along with p-value",
            "✓ Consider multiple testing correction for many tests"
        ]
    },
    "multivariate_analysis": {
        "title": "Multivariate Analysis Best Practices",
        "practices": [
            "✓ Check assumptions (linearity, normality, homoscedasticity)",
            "✓ Inspect diagnostic plots (residuals, Q-Q, scale-location)",
            "✓ Check for multicollinearity (VIF < 5)",
            "✓ Avoid overfitting (limit predictors relative to sample size)",
            "✓ Use adjusted R² for multiple predictors",
            "✓ Consider interaction terms when theoretically justified",
            "✓ Validate model on holdout data when possible"
        ]
    },
    "auto_triage": {
        "title": "Auto-Triage Best Practices",
        "practices": [
            "✓ Use for exploratory analysis, not confirmatory",
            "✓ Investigate high-suspicion variables manually",
            "✓ Consider domain knowledge when interpreting flags",
            "✓ Check multiple indicators (PCA, change-points, clusters)",
            "✓ Document triage decisions for audit trail",
            "✓ Validate suspicious patterns with subject matter experts",
            "✓ Use results to guide focused analysis"
        ]
    }
}


def render_help_icon(
    topic: str,
    label: Optional[str] = None,
    position: str = "inline"
) -> None:
    """Render a help icon with tooltip.
    
    Args:
        topic: Help topic key
        label: Optional label to display with icon
        position: Position of help icon ('inline' or 'sidebar')
    """
    help_content = _get_help_content(topic)
    
    if not help_content:
        return
    
    if position == "inline":
        if label:
            st.markdown(f"**{label}** ℹ️", help=help_content)
        else:
            st.markdown("ℹ️", help=help_content)
    else:
        with st.sidebar:
            with st.expander(f"ℹ️ {label or 'Help'}", expanded=False):
                st.markdown(help_content)


def render_method_help(method: str) -> None:
    """Render detailed help for a statistical method.
    
    Args:
        method: Method key (e.g., 'pearson', 'regression')
    """
    if method not in STATISTICAL_METHODS:
        st.warning(f"No help available for method: {method}")
        return
    
    info = STATISTICAL_METHODS[method]
    
    st.markdown(f"### {info['name']}")
    st.markdown(f"**Description:** {info['description']}")
    
    st.markdown("**Assumptions:**")
    for assumption in info['assumptions']:
        st.markdown(f"- {assumption}")
    
    st.markdown(f"**Interpretation:** {info['interpretation']}")
    st.markdown(f"**When to Use:** {info['when_to_use']}")


def render_interpretation_guide(guide_key: str) -> None:
    """Render an interpretation guide.
    
    Args:
        guide_key: Guide identifier
    """
    if guide_key not in INTERPRETATION_GUIDES:
        st.warning(f"No guide available: {guide_key}")
        return
    
    guide = INTERPRETATION_GUIDES[guide_key]
    
    st.markdown(f"### {guide['title']}")
    st.markdown(guide['content'])


def render_best_practices(topic: str) -> None:
    """Render best practices for a topic.
    
    Args:
        topic: Best practices topic
    """
    if topic not in BEST_PRACTICES:
        st.warning(f"No best practices available: {topic}")
        return
    
    practices = BEST_PRACTICES[topic]
    
    st.markdown(f"### {practices['title']}")
    for practice in practices['practices']:
        st.markdown(practice)


def render_quick_help() -> None:
    """Render quick help sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ❓ Quick Help")
        
        help_topic = st.selectbox(
            "Select Help Topic",
            options=[
                "Getting Started",
                "Understanding Results",
                "Statistical Methods",
                "Best Practices",
                "Troubleshooting"
            ],
            key="quick_help_topic"
        )
        
        if help_topic == "Getting Started":
            st.markdown("""
            **Quick Start Guide:**
            1. Upload your dataset
            2. Configure analysis settings
            3. Select analysis mode
            4. Run analysis
            5. Interpret results
            
            [Full Documentation](#)
            """)
        
        elif help_topic == "Understanding Results":
            st.markdown("""
            **Key Metrics:**
            - **Correlation (r)**: Strength of relationship
            - **P-value**: Statistical significance
            - **R²**: Variance explained
            - **VIF**: Multicollinearity check
            
            Click ℹ️ icons for details
            """)
        
        elif help_topic == "Statistical Methods":
            method = st.selectbox(
                "Method",
                options=list(STATISTICAL_METHODS.keys()),
                format_func=lambda x: STATISTICAL_METHODS[x]['name']
            )
            render_method_help(method)
        
        elif help_topic == "Best Practices":
            practice_topic = st.selectbox(
                "Topic",
                options=list(BEST_PRACTICES.keys()),
                format_func=lambda x: BEST_PRACTICES[x]['title']
            )
            render_best_practices(practice_topic)
        
        elif help_topic == "Troubleshooting":
            st.markdown("""
            **Common Issues:**
            
            **Analysis Fails:**
            - Check data quality
            - Verify column types
            - Review configuration
            
            **Unexpected Results:**
            - Check assumptions
            - Inspect data visually
            - Review preprocessing
            
            **Performance Issues:**
            - Enable sampling
            - Reduce variables
            - Use caching
            
            [Report Issue](#)
            """)


def _get_help_content(topic: str) -> Optional[str]:
    """Get help content for a topic.
    
    Args:
        topic: Help topic key
    
    Returns:
        Help content string or None
    """
    # Check statistical methods
    if topic in STATISTICAL_METHODS:
        info = STATISTICAL_METHODS[topic]
        return f"{info['description']}\n\n{info['interpretation']}"
    
    # Check interpretation guides
    if topic in INTERPRETATION_GUIDES:
        return INTERPRETATION_GUIDES[topic]['content']
    
    # Check best practices
    if topic in BEST_PRACTICES:
        practices = BEST_PRACTICES[topic]['practices']
        return "\n".join(practices)
    
    return None
