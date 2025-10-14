"""AI-generated summary component for analysis results.

Provides collapsible summary sections with AI-generated insights
(placeholder implementation for future LLM integration).
"""

import streamlit as st
from typing import Dict, Any, List, Optional


def render_ai_summary(result_data: Dict[str, Any], analysis_mode: str) -> None:
    """Render AI-generated summary of analysis results.
    
    Args:
        result_data: Complete analysis result dictionary
        analysis_mode: Type of analysis ('correlation', 'multivariate', 'auto-triage')
    """
    with st.expander("🤖 AI-Generated Summary", expanded=False):
        st.markdown("### Analysis Insights")
        
        # Mode-specific summary generation
        if analysis_mode == "correlation":
            _render_correlation_summary(result_data)
        elif analysis_mode == "multivariate":
            _render_multivariate_summary(result_data)
        elif analysis_mode == "auto-triage":
            _render_autotriage_summary(result_data)
        else:
            st.info("Summary not available for this analysis mode")
        
        st.divider()
        st.caption("💡 This is a rule-based summary. Future versions will use LLM integration for richer insights.")


def _render_correlation_summary(result_data: Dict[str, Any]) -> None:
    """Generate summary for correlation analysis.
    
    Args:
        result_data: Correlation analysis results
    """
    table = result_data.get("correlation_table", {})
    records = table.get("records", [])
    
    if not records:
        st.info("No correlation data to summarize")
        return
    
    # Calculate summary statistics
    num_pairs = len(records)
    coefficients = [r.get('coefficient', 0) for r in records]
    p_values = [r.get('p_value', 1) for r in records if r.get('p_value') is not None]
    
    avg_corr = sum(abs(c) for c in coefficients) / len(coefficients) if coefficients else 0
    significant = sum(1 for p in p_values if p < 0.05)
    
    # Find strongest correlations
    sorted_records = sorted(records, key=lambda r: abs(r.get('coefficient', 0)), reverse=True)
    top_3 = sorted_records[:3]
    
    # Generate narrative summary
    st.markdown(f"""
    **Key Findings:**
    
    - Analyzed **{num_pairs}** variable pairs
    - Average absolute correlation: **{avg_corr:.3f}**
    - **{significant}** pairs significant at p < 0.05 ({significant/len(p_values)*100 if p_values else 0:.1f}%)
    
    **Strongest Correlations:**
    """)
    
    for i, record in enumerate(top_3, 1):
        vars = record.get('variables', [])
        coef = record.get('coefficient', 0)
        p_val = record.get('p_value', 1)
        
        if isinstance(vars, (list, tuple)) and len(vars) == 2:
            direction = "positive" if coef > 0 else "negative"
            strength = _interpret_correlation_strength(abs(coef))
            sig = "✓ significant" if p_val < 0.05 else "not significant"
            
            st.markdown(f"{i}. **`{vars[0]}`** ↔ **`{vars[1]}`**: {strength} {direction} correlation (r={coef:.3f}, {sig})")
    
    # Interpretation
    st.markdown("""
    **Interpretation:**
    """)
    
    if avg_corr < 0.3:
        st.info("Overall correlations are weak, suggesting variables are largely independent.")
    elif avg_corr < 0.6:
        st.info("Moderate correlations detected, indicating some relationships between variables.")
    else:
        st.warning("Strong correlations present. Consider multicollinearity if using for regression.")


def _render_multivariate_summary(result_data: Dict[str, Any]) -> None:
    """Generate summary for multivariate analysis.
    
    Args:
        result_data: Multivariate analysis results
    """
    summary = result_data.get("model_summary", {})
    
    if not summary:
        st.info("No model data to summarize")
        return
    
    # Extract key metrics
    r_squared = summary.get('r_squared', 0)
    adj_r_squared = summary.get('adj_r_squared', 0)
    n_obs = summary.get('n_observations', 0)
    target = summary.get('target_variable', 'Unknown')
    coefficients = summary.get('coefficients', [])
    
    # Find significant predictors
    significant_predictors = [
        c for c in coefficients
        if c.get('p_value', 1) < 0.05 and c.get('variable') != 'Intercept'
    ]
    
    # Model quality assessment
    if r_squared >= 0.7:
        quality = "strong"
        quality_emoji = "✅"
    elif r_squared >= 0.4:
        quality = "moderate"
        quality_emoji = "⚠️"
    else:
        quality = "weak"
        quality_emoji = "❌"
    
    st.markdown(f"""
    **Model Performance:** {quality_emoji}
    
    - Target variable: **`{target}`**
    - Model explains **{r_squared*100:.1f}%** of variance (R² = {r_squared:.3f})
    - Adjusted R²: **{adj_r_squared:.3f}** (accounts for number of predictors)
    - Sample size: **{n_obs}** observations
    - **{len(significant_predictors)}** of {len(coefficients)-1} predictors are significant
    
    **Model Quality:** {quality.capitalize()} ({quality_emoji})
    """)
    
    # Significant predictors
    if significant_predictors:
        st.markdown("**Significant Predictors:**")
        
        for pred in significant_predictors[:5]:  # Top 5
            var = pred.get('variable', 'Unknown')
            coef = pred.get('coefficient', 0)
            p_val = pred.get('p_value', 1)
            
            direction = "increases" if coef > 0 else "decreases"
            st.markdown(f"- **`{var}`**: {direction} target (β={coef:.3f}, p={p_val:.4f})")
    
    # Recommendations
    st.markdown("**Recommendations:**")
    
    if r_squared < 0.4:
        st.warning("Consider adding more predictors or checking for non-linear relationships.")
    elif len(significant_predictors) < len(coefficients) * 0.5:
        st.info("Many predictors are not significant. Consider feature selection or regularization.")
    else:
        st.success("Model shows good fit with meaningful predictors.")


def _render_autotriage_summary(result_data: Dict[str, Any]) -> None:
    """Generate summary for auto-triage analysis.
    
    Args:
        result_data: Auto-triage analysis results
    """
    rankings = result_data.get('suspicion_rankings', [])
    
    if not rankings:
        st.info("No triage data to summarize")
        return
    
    # Categorize by severity
    high_suspicion = [r for r in rankings if r.get('total_score', 0) >= 70]
    medium_suspicion = [r for r in rankings if 40 <= r.get('total_score', 0) < 70]
    low_suspicion = [r for r in rankings if r.get('total_score', 0) < 40]
    
    total_cols = len(rankings)
    
    st.markdown(f"""
    **Quality Assessment:**
    
    - Total columns analyzed: **{total_cols}**
    - 🔴 High suspicion: **{len(high_suspicion)}** columns ({len(high_suspicion)/total_cols*100 if total_cols else 0:.1f}%)
    - 🟡 Medium suspicion: **{len(medium_suspicion)}** columns ({len(medium_suspicion)/total_cols*100 if total_cols else 0:.1f}%)
    - 🟢 Low suspicion: **{len(low_suspicion)}** columns ({len(low_suspicion)/total_cols*100 if total_cols else 0:.1f}%)
    """)
    
    # High suspicion details
    if high_suspicion:
        st.markdown("**⚠️ Columns Requiring Attention:**")
        
        for col_data in high_suspicion[:5]:  # Top 5
            col_name = col_data.get('column_name', 'Unknown')
            score = col_data.get('total_score', 0)
            
            # Identify main issues
            issues = []
            if col_data.get('missing_score', 0) > 20:
                issues.append("high missing data")
            if col_data.get('outlier_score', 0) > 20:
                issues.append("many outliers")
            if col_data.get('distribution_score', 0) > 20:
                issues.append("unusual distribution")
            
            issue_str = ", ".join(issues) if issues else "multiple quality concerns"
            st.markdown(f"- **`{col_name}`** (score: {score:.1f}): {issue_str}")
    
    # Overall data quality
    st.markdown("**Overall Data Quality:**")
    
    if len(high_suspicion) == 0:
        st.success("✅ No major quality issues detected. Data appears clean.")
    elif len(high_suspicion) <= total_cols * 0.2:
        st.info("ℹ️ Minor quality issues in some columns. Review flagged columns.")
    else:
        st.error("❌ Significant quality issues detected. Recommend thorough data cleaning.")
    
    # Recommended actions
    st.markdown("**Recommended Actions:**")
    
    if high_suspicion:
        st.markdown("""
        1. Investigate high-suspicion columns for data collection issues
        2. Consider imputation strategies for missing data
        3. Review outliers to determine if they're errors or valid extreme values
        4. Document any data quality decisions in your workflow
        """)
    else:
        st.markdown("No immediate actions required. Proceed with analysis.")


def _interpret_correlation_strength(abs_corr: float) -> str:
    """Interpret correlation strength.
    
    Args:
        abs_corr: Absolute value of correlation coefficient
    
    Returns:
        String description of strength
    """
    if abs_corr >= 0.7:
        return "strong"
    elif abs_corr >= 0.4:
        return "moderate"
    elif abs_corr >= 0.2:
        return "weak"
    else:
        return "very weak"
