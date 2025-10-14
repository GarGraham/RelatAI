"""Multivariate analysis visualization components.

Provides model summary, coefficient plots, and diagnostic visualizations
for multivariate regression analysis results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
import numpy as np


def render_multivariate_results(result_data: Dict[str, Any]) -> None:
    """Render complete multivariate analysis results with all visualizations.
    
    Args:
        result_data: Multivariate result dictionary containing:
            - model_summary: dict with coefficients, r_squared, etc.
            - residuals: array of residuals
            - fitted_values: array of fitted values
            - quality_flags: list of flags
    """
    if not result_data or "model_summary" not in result_data:
        st.warning("No multivariate data available")
        return
    
    summary = result_data["model_summary"]
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs([
        "📋 Model Summary",
        "📊 Coefficients",
        "🔍 Diagnostics"
    ])
    
    with tab1:
        render_model_summary(summary, result_data)
    
    with tab2:
        render_coefficient_plot(summary)
    
    with tab3:
        render_diagnostics(result_data)


def render_model_summary(summary: Dict[str, Any], full_result: Dict[str, Any]) -> None:
    """Render model summary statistics and fit metrics.
    
    Args:
        summary: Model summary dictionary
        full_result: Full result data for additional metrics
    """
    st.subheader("Model Summary")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        r_squared = summary.get('r_squared', 0)
        st.metric("R²", f"{r_squared:.4f}")
    
    with col2:
        adj_r_squared = summary.get('adj_r_squared', 0)
        st.metric("Adj. R²", f"{adj_r_squared:.4f}")
    
    with col3:
        n_obs = summary.get('n_observations', 0)
        st.metric("Observations", n_obs)
    
    with col4:
        n_predictors = len(summary.get('coefficients', []))
        st.metric("Predictors", n_predictors)
    
    st.divider()
    
    # Target variable info
    target = summary.get('target_variable', 'Unknown')
    st.markdown(f"**Target Variable:** `{target}`")
    
    # Coefficient table
    st.markdown("#### Regression Coefficients")
    
    coefficients = summary.get('coefficients', [])
    if coefficients:
        df = pd.DataFrame(coefficients)
        
        # Format columns for display
        display_df = pd.DataFrame({
            'Variable': df['variable'],
            'Coefficient': df['coefficient'].apply(lambda x: f"{x:.4f}"),
            'Std Error': df.get('std_error', pd.Series([None]*len(df))).apply(
                lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
            ),
            'T-Statistic': df.get('t_statistic', pd.Series([None]*len(df))).apply(
                lambda x: f"{x:.3f}" if pd.notna(x) else "N/A"
            ),
            'P-Value': df.get('p_value', pd.Series([None]*len(df))).apply(
                lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
            ),
            'Significant': df.get('p_value', pd.Series([1.0]*len(df))).apply(
                lambda x: "✓" if x < 0.05 else ""
            )
        })
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(display_df) * 35 + 38)
        )
    else:
        st.info("No coefficient data available")
    
    # Additional statistics in expander
    with st.expander("📊 Additional Statistics"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Goodness of Fit**")
            aic = summary.get('aic')
            bic = summary.get('bic')
            
            if aic is not None:
                st.text(f"AIC: {aic:.2f}")
            if bic is not None:
                st.text(f"BIC: {bic:.2f}")
            
            residual_std = summary.get('residual_std_error')
            if residual_std is not None:
                st.text(f"Residual Std Error: {residual_std:.4f}")
        
        with col2:
            st.markdown("**F-Statistic**")
            f_stat = summary.get('f_statistic')
            f_pvalue = summary.get('f_pvalue')
            
            if f_stat is not None:
                st.text(f"F-Statistic: {f_stat:.3f}")
            if f_pvalue is not None:
                st.text(f"P-Value: {f_pvalue:.4e}")
                st.text(f"Significant: {'Yes' if f_pvalue < 0.05 else 'No'}")


def render_coefficient_plot(summary: Dict[str, Any]) -> None:
    """Render coefficient plot with confidence intervals.
    
    Args:
        summary: Model summary dictionary
    """
    st.subheader("Coefficient Plot")
    
    coefficients = summary.get('coefficients', [])
    if not coefficients:
        st.info("No coefficient data available")
        return
    
    df = pd.DataFrame(coefficients)
    
    # Exclude intercept option
    exclude_intercept = st.checkbox(
        "Exclude Intercept",
        value=True,
        key="exclude_intercept"
    )
    
    if exclude_intercept:
        df = df[df['variable'] != 'Intercept'].copy()
    
    if len(df) == 0:
        st.info("No coefficients to display")
        return
    
    # Calculate confidence intervals if std_error available
    has_std_error = 'std_error' in df.columns and df['std_error'].notna().any()
    
    if has_std_error:
        # 95% confidence interval (1.96 * std_error)
        df['ci_lower'] = df['coefficient'] - 1.96 * df['std_error']
        df['ci_upper'] = df['coefficient'] + 1.96 * df['std_error']
    
    # Sort by absolute coefficient value
    df['abs_coef'] = df['coefficient'].abs()
    df = df.sort_values('abs_coef', ascending=True)
    
    # Create figure
    fig = go.Figure()
    
    # Add coefficient bars
    colors = ['green' if c > 0 else 'red' for c in df['coefficient']]
    
    fig.add_trace(go.Bar(
        y=df['variable'],
        x=df['coefficient'],
        orientation='h',
        marker=dict(color=colors),
        name='Coefficient',
        text=df['coefficient'].apply(lambda x: f"{x:.3f}"),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Coefficient: %{x:.4f}<extra></extra>'
    ))
    
    # Add confidence intervals if available
    if has_std_error:
        for idx, row in df.iterrows():
            fig.add_trace(go.Scatter(
                x=[row['ci_lower'], row['ci_upper']],
                y=[row['variable'], row['variable']],
                mode='lines',
                line=dict(color='black', width=2),
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # Add reference line at 0
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        title="Regression Coefficients with 95% CI",
        xaxis_title="Coefficient Value",
        yaxis_title="",
        height=max(400, len(df) * 30),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Interpretation guide
    with st.expander("📖 Interpretation Guide"):
        st.markdown("""
        **How to read this plot:**
        - **Green bars**: Positive coefficients (increase in predictor → increase in target)
        - **Red bars**: Negative coefficients (increase in predictor → decrease in target)
        - **Black lines**: 95% confidence intervals
        - **Significance**: If CI crosses zero, coefficient may not be significant
        """)


def render_diagnostics(result_data: Dict[str, Any]) -> None:
    """Render diagnostic plots for model validation.
    
    Args:
        result_data: Full result dictionary with residuals and fitted values
    """
    st.subheader("Model Diagnostics")
    
    residuals = result_data.get('residuals', [])
    fitted = result_data.get('fitted_values', [])
    
    if not residuals or not fitted:
        st.info("Diagnostic data not available")
        return
    
    residuals = np.array(residuals)
    fitted = np.array(fitted)
    
    # Create 2x2 diagnostic plot layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Residuals vs Fitted
        fig1 = go.Figure()
        
        fig1.add_trace(go.Scatter(
            x=fitted,
            y=residuals,
            mode='markers',
            marker=dict(color='blue', size=5, opacity=0.6),
            name='Residuals'
        ))
        
        # Add horizontal line at 0
        fig1.add_hline(y=0, line_dash="dash", line_color="red")
        
        # Add LOWESS smoothing line (simple moving average approximation)
        if len(fitted) > 10:
            sorted_idx = np.argsort(fitted)
            window = max(len(fitted) // 10, 5)
            smoothed = pd.Series(residuals[sorted_idx]).rolling(window, center=True).mean()
            
            fig1.add_trace(go.Scatter(
                x=fitted[sorted_idx],
                y=smoothed,
                mode='lines',
                line=dict(color='red', width=2),
                name='Trend'
            ))
        
        fig1.update_layout(
            title="Residuals vs Fitted",
            xaxis_title="Fitted Values",
            yaxis_title="Residuals",
            height=350,
            showlegend=False
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Q-Q Plot
        from scipy import stats
        
        # Standardize residuals
        std_residuals = (residuals - np.mean(residuals)) / np.std(residuals)
        
        # Theoretical quantiles
        n = len(std_residuals)
        theoretical = stats.norm.ppf(np.linspace(0.01, 0.99, n))
        sample = np.sort(std_residuals)
        
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=theoretical,
            y=sample,
            mode='markers',
            marker=dict(color='blue', size=5, opacity=0.6),
            name='Sample'
        ))
        
        # Add reference line
        fig2.add_trace(go.Scatter(
            x=[theoretical.min(), theoretical.max()],
            y=[theoretical.min(), theoretical.max()],
            mode='lines',
            line=dict(color='red', dash='dash'),
            name='Theoretical'
        ))
        
        fig2.update_layout(
            title="Normal Q-Q Plot",
            xaxis_title="Theoretical Quantiles",
            yaxis_title="Sample Quantiles",
            height=350,
            showlegend=False
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # Second row
    col3, col4 = st.columns(2)
    
    with col3:
        # Scale-Location plot
        sqrt_abs_residuals = np.sqrt(np.abs(residuals))
        
        fig3 = go.Figure()
        
        fig3.add_trace(go.Scatter(
            x=fitted,
            y=sqrt_abs_residuals,
            mode='markers',
            marker=dict(color='blue', size=5, opacity=0.6),
            name='Residuals'
        ))
        
        # Add smoothing line
        if len(fitted) > 10:
            sorted_idx = np.argsort(fitted)
            window = max(len(fitted) // 10, 5)
            smoothed = pd.Series(sqrt_abs_residuals[sorted_idx]).rolling(window, center=True).mean()
            
            fig3.add_trace(go.Scatter(
                x=fitted[sorted_idx],
                y=smoothed,
                mode='lines',
                line=dict(color='red', width=2),
                name='Trend'
            ))
        
        fig3.update_layout(
            title="Scale-Location",
            xaxis_title="Fitted Values",
            yaxis_title="√|Residuals|",
            height=350,
            showlegend=False
        )
        
        st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        # Residuals Histogram
        fig4 = go.Figure()
        
        fig4.add_trace(go.Histogram(
            x=residuals,
            nbinsx=30,
            marker=dict(color='blue', opacity=0.7),
            name='Residuals'
        ))
        
        # Overlay normal curve
        x_range = np.linspace(residuals.min(), residuals.max(), 100)
        normal_curve = stats.norm.pdf(x_range, np.mean(residuals), np.std(residuals))
        # Scale to match histogram
        normal_curve = normal_curve * len(residuals) * (residuals.max() - residuals.min()) / 30
        
        fig4.add_trace(go.Scatter(
            x=x_range,
            y=normal_curve,
            mode='lines',
            line=dict(color='red', width=2),
            name='Normal'
        ))
        
        fig4.update_layout(
            title="Residuals Distribution",
            xaxis_title="Residuals",
            yaxis_title="Frequency",
            height=350,
            showlegend=False
        )
        
        st.plotly_chart(fig4, use_container_width=True)
    
    # Diagnostic interpretation
    with st.expander("📖 Diagnostic Interpretation"):
        st.markdown("""
        **Residuals vs Fitted:**
        - Should show random scatter around zero
        - Patterns indicate model issues (non-linearity, heteroscedasticity)
        
        **Q-Q Plot:**
        - Points should follow diagonal line
        - Deviations indicate non-normal residuals
        
        **Scale-Location:**
        - Should show horizontal trend
        - Increasing/decreasing trend indicates heteroscedasticity
        
        **Residuals Distribution:**
        - Should approximate normal distribution
        - Heavy tails or skewness indicate assumption violations
        """)
