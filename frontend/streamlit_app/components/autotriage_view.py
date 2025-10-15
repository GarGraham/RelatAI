"""Auto-triage analysis visualization components.

Provides enhanced suspicion rankings with contribution breakdowns, PCA biplot
with narratives, change-point detection with segment summaries, and cluster
deep-dive visualizations for automated quality triage results.

This module implements the frontend components for DataUnderstanding_v2.md plan,
supporting both legacy and enhanced payloads during migration.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional
import numpy as np
import io
import pathlib

# Import navigation and state management
from utils.autotriage_state import (
    get_autotriage_state,
    set_active_autotriage_tab,
    render_navigation_breadcrumb,
    get_navigation_from_link,
)
from utils.navigation import sync_state_from_url, set_query_params
from components.confidence_flags import render_flags_inline


# ==============================================================================
# CSS INJECTION
# ==============================================================================

def inject_autotriage_css():
    """Inject responsive CSS for auto-triage components.
    
    Implements DataUnderstanding_v2.md Section 2.6 responsive design specification.
    CSS is loaded from assets/autotriage.css and injected once per session.
    """
    if "autotriage_css_injected" not in st.session_state:
        try:
            # Get path to CSS file
            css_path = pathlib.Path(__file__).parent.parent / "assets" / "autotriage.css"
            
            if css_path.exists():
                with open(css_path, "r", encoding="utf-8") as f:
                    css_content = f.read()
                
                # Inject CSS
                st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
                
                st.session_state["autotriage_css_injected"] = True
            else:
                # Silently fail if CSS file not found (dev mode)
                pass
        except Exception as e:
            # Don't break rendering if CSS injection fails
            import warnings
            warnings.warn(f"Failed to inject auto-triage CSS: {e}")
            st.session_state["autotriage_css_injected"] = True  # Prevent retry loops


def render_autotriage_results(result_data: Dict[str, Any]) -> None:
    """Render complete auto-triage analysis results with enhanced visualizations.
    
    Supports both legacy and enhanced payloads:
    - Legacy: suspicion_rankings, pca_components, change_points, clusters
    - Enhanced: suspicion_items, pca_explain, change_point_reports, cluster_profile
    
    Args:
        result_data: Auto-triage result dictionary from backend
    """
    if not result_data:
        st.warning("No auto-triage data available")
        return
    
    # Inject responsive CSS
    inject_autotriage_css()
    
    # Sync state from URL on initial load
    sync_state_from_url()
    
    # Render navigation breadcrumb
    render_navigation_breadcrumb()
    
    # Get current state
    state = get_autotriage_state()
    
    # Detect payload type (enhanced vs legacy)
    has_enhanced = (
        'suspicion_items' in result_data or
        'pca_explain' in result_data or
        'change_point_reports' in result_data or
        'cluster_profile' in result_data
    )
    
    # Create tabs for different visualizations
    tab_names = ["🎯 Suspicion Rankings", "📊 PCA Analysis", "📈 Change Points", "🔵 Clusters"]
    tabs = st.tabs(tab_names)
    
    # Note: Tab navigation is handled by state management (autotriage_state.py) and button
    # callbacks with st.rerun(). Streamlit tabs API doesn't support programmatic activation.
    
    with tabs[0]:  # Suspicion Rankings
        if has_enhanced and 'suspicion_items' in result_data:
            render_suspicion_rankings_enhanced(
                result_data.get('suspicion_items', []),
                result_data.get('quality_flags', [])
            )
        else:
            render_suspicion_rankings_legacy(result_data.get('suspicion_rankings', []))
    
    with tabs[1]:  # PCA Analysis
        if has_enhanced and 'pca_explain' in result_data:
            render_pca_enhanced(result_data.get('pca_explain'))
        else:
            render_pca_legacy(result_data.get('pca_components', []))
    
    with tabs[2]:  # Change Points
        if has_enhanced and 'change_point_reports' in result_data:
            render_change_points_enhanced(result_data.get('change_point_reports', []))
        else:
            render_change_points_legacy(result_data.get('change_points', []))
    
    with tabs[3]:  # Clusters
        if has_enhanced and 'cluster_profile' in result_data:
            render_clusters_enhanced(result_data.get('cluster_profile'))
        else:
            render_clusters_legacy(result_data.get('clusters', []))


# ==============================================================================
# SUSPICION RANKINGS TAB
# ==============================================================================

def render_suspicion_rankings_enhanced(
    suspicion_items: List[Dict[str, Any]],
    quality_flags: List[Dict[str, Any]]
) -> None:
    """Render enhanced suspicion rankings with contribution breakdown.
    
    Displays ranked card layout with stacked bar charts showing signal
    contributions, quality flags, and navigation links to other tabs.
    
    Args:
        suspicion_items: List of SuspicionItemModel dictionaries with:
            - target: str
            - score: float (0-1)
            - contrib: dict[str, float] (signal contributions)
            - top_signals: list[SignalDetail]
            - links: dict[str, str]
            - flags: list[str]
        quality_flags: List of quality flag dictionaries
    """
    st.subheader("🎯 Suspicion Rankings - Enhanced View")
    
    if not suspicion_items:
        st.info("No suspicion items available")
        return
    
    # Filter controls
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search targets", key="suspicion_search")
    with col2:
        show_all = st.checkbox("Show all", value=len(suspicion_items) <= 10, key="suspicion_show_all")
    
    # Filter by search
    filtered_items = suspicion_items
    if search:
        filtered_items = [
            item for item in suspicion_items
            if search.lower() in item.get('target', '').lower()
        ]
    
    # Limit display if not showing all
    display_items = filtered_items if show_all else filtered_items[:10]
    
    # Render each suspicion item as a card
    for idx, item in enumerate(display_items):
        target = item.get('target', 'Unknown')
        score = item.get('score', 0.0)
        contrib = item.get('contrib', {})
        top_signals = item.get('top_signals', [])
        links = item.get('links', {})
        flags = item.get('flags', [])
        
        # Determine severity color
        if score >= 0.7:
            severity_color = "🔴"
            severity_label = "High"
        elif score >= 0.4:
            severity_color = "🟡"
            severity_label = "Medium"
        else:
            severity_color = "🟢"
            severity_label = "Low"
        
        # Create card container
        with st.container():
            st.markdown(f"### {severity_color} #{idx + 1}: {target}")
            
            card_col1, card_col2 = st.columns([2, 1])
            
            with card_col1:
                # Score and severity
                st.metric("Suspicion Score", f"{score * 100:.1f}%", delta=severity_label)
                
                # Contribution breakdown (stacked bar)
                if contrib:
                    st.markdown("**Signal Contributions:**")
                    fig_contrib = go.Figure()
                    
                    # Sort contributions by value
                    sorted_contrib = sorted(contrib.items(), key=lambda x: x[1], reverse=True)
                    
                    colors = {
                        'pca_loading': '#1f77b4',  # Blue
                        'changepoint': '#ff7f0e',  # Orange
                        'cluster': '#2ca02c',      # Green
                        'residual': '#d62728',     # Red
                        'dispersion': '#9467bd'    # Purple
                    }
                    
                    for signal_type, value in sorted_contrib:
                        fig_contrib.add_trace(go.Bar(
                            name=signal_type.replace('_', ' ').title(),
                            x=[value * 100],
                            y=['Contribution'],
                            orientation='h',
                            marker=dict(color=colors.get(signal_type, '#cccccc')),
                            text=f"{value * 100:.1f}%",
                            textposition='inside',
                            hovertemplate=f"{signal_type}: {value * 100:.1f}%<extra></extra>"
                        ))
                    
                    fig_contrib.update_layout(
                        barmode='stack',
                        height=80,
                        margin=dict(l=0, r=0, t=0, b=0),
                        showlegend=False,
                        xaxis=dict(showticklabels=False, showgrid=False),
                        yaxis=dict(showticklabels=False),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    
                    st.plotly_chart(fig_contrib, use_container_width=True, key=f"contrib_{target}_{idx}")
                
                # Top signals (evidence bullets)
                if top_signals:
                    st.markdown("**Evidence:**")
                    for signal in top_signals[:3]:  # Show top 3
                        detail = signal.get('detail', '')
                        weight = signal.get('weight', 0.0)
                        st.markdown(f"- {detail} ({weight:.2f})")
            
            with card_col2:
                # Quality flags
                if flags:
                    st.markdown("**Quality Flags:**")
                    render_flags_inline(flags)
                
                # Navigation links
                if links:
                    st.markdown("**Jump to:**")
                    for link_key, link_value in links.items():
                        if link_key == 'pca_component' and link_value:
                            if st.button(f"📊 PC{link_value}", key=f"nav_pca_{target}_{idx}"):
                                set_active_autotriage_tab("pca", {"component": link_value}, "suspicion")
                                st.rerun()
                        elif link_key == 'changepoint_tab' and link_value:
                            if st.button(f"📈 Change Points", key=f"nav_cp_{target}_{idx}"):
                                set_active_autotriage_tab("changepoints", {"column": link_value}, "suspicion")
                                st.rerun()
                        elif link_key == 'cluster_profile' and link_value:
                            if st.button(f"🔵 Clusters", key=f"nav_clust_{target}_{idx}"):
                                set_active_autotriage_tab("clusters", {"column": link_value}, "suspicion")
                                st.rerun()
            
            st.divider()
    
    # Summary statistics
    if len(filtered_items) > len(display_items):
        st.info(f"Showing {len(display_items)} of {len(filtered_items)} items. Enable 'Show all' to see more.")


def render_suspicion_rankings_legacy(rankings: List[Dict[str, Any]]) -> None:
    """Render suspicion rankings table (legacy format).
    
    Args:
        rankings: List of RankedInsightModel dictionaries from backend with:
            - label: str (column or feature name)
            - score: float (0.0 to 1.0)
            - drivers: list of str (reasons for suspicion)
            - category: str
            - method: str (optional)
    """
    st.subheader("🎯 Suspicion Rankings")
    
    if not rankings:
        st.info("No suspicion rankings available")
        return
    
    # Convert to DataFrame and sort by score
    df = pd.DataFrame(rankings)
    df = df.sort_values('score', ascending=False)
    
    # Normalize score to percentage and create severity categories
    df['score_pct'] = df['score'] * 100
    
    def categorize_score(score_pct):
        if score_pct >= 70:
            return "🔴 High"
        elif score_pct >= 40:
            return "🟡 Medium"
        else:
            return "🟢 Low"
    
    df['Severity'] = df['score_pct'].apply(categorize_score)
    
    # Format display columns
    display_df = pd.DataFrame({
        'Rank': range(1, len(df) + 1),
        'Target': df['label'],
        'Score': df['score_pct'].apply(lambda x: f"{x:.1f}%"),
        'Severity': df['Severity'],
        'Category': df.get('category', 'general')
    })
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Detailed breakdown for selected item
    st.divider()
    st.markdown("#### Detailed Breakdown")
    
    selected_item = st.selectbox(
        "Select item for detailed breakdown",
        options=df['label'].tolist(),
        key="suspicion_detail"
    )
    
    if selected_item:
        row = df[df['label'] == selected_item].iloc[0]
        
        st.markdown(f"**Target:** {selected_item}")
        st.markdown(f"**Score:** {row['score_pct']:.1f}%")
        st.markdown(f"**Category:** {row.get('category', 'general')}")
        
        # Display drivers (reasons for suspicion)
        drivers = row.get('drivers', [])
        if drivers:
            st.markdown("**Reasons for Suspicion:**")
            for driver in drivers:
                st.markdown(f"- {driver}")
        else:
            st.info("No detailed drivers available")
        
        # Additional metadata
        metadata = row.get('metadata', {})
        if metadata:
            with st.expander("Additional Details"):
                st.json(metadata)
    
    # Summary statistics
    with st.expander("📊 Summary"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_suspicion = (df['score_pct'] >= 70).sum()
            st.metric("High Suspicion", high_suspicion)
        
        with col2:
            medium_suspicion = ((df['score_pct'] >= 40) & (df['score_pct'] < 70)).sum()
            st.metric("Medium Suspicion", medium_suspicion)
        
        with col3:
            low_suspicion = (df['score_pct'] < 40).sum()
            st.metric("Low Suspicion", low_suspicion)


# ==============================================================================
# PCA TAB  
# ==============================================================================

def render_pca_enhanced(pca_explain: Optional[Dict[str, Any]]) -> None:
    """Render enhanced PCA analysis with narrative explanations.
    
    Implements DataUnderstanding_v2.md Section 2.2 specification with:
    - Two-panel layout: variance overview + narrative feed
    - Bar chart + cumulative line for variance explained
    - Plain-English PC interpretations
    - Loadings table with CSV download
    - Compare Components toggle with radar chart
    
    Args:
        pca_explain: PCAExplainModel dictionary with:
            - variance: list[dict] with {'pc': str, 'ratio': float}
            - loadings: dict[str, list[tuple[str, float]]] (PC -> features)
            - narrative: list[str] (plain-English interpretations)
            - cumulative_variance: float (total variance explained)
    """
    st.subheader("📊 PCA Analysis - Enhanced View")
    
    if not pca_explain:
        st.info("PCA explanation data not available")
        return
    
    variance = pca_explain.get('variance', [])
    loadings = pca_explain.get('loadings', {})
    narratives = pca_explain.get('narrative', [])
    cumulative_variance = pca_explain.get('cumulative_variance', 0.0)
    
    if not variance:
        st.info("No PCA variance data available")
        return
    
    # Two-panel layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Variance Overview")
        
        # Prepare data for variance chart
        pc_names = [v['pc'] for v in variance]
        ratios = [v['ratio'] * 100 for v in variance]
        cumulative_ratios = np.cumsum(ratios).tolist()
        
        # Create bar + line chart using Plotly
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Bar chart for individual variance
        fig.add_trace(
            go.Bar(
                x=pc_names,
                y=ratios,
                name='Variance Explained',
                marker_color='#1f77b4',
                text=[f"{r:.1f}%" for r in ratios],
                textposition='outside',
                hovertemplate='%{x}: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=False
        )
        
        # Line chart for cumulative variance
        fig.add_trace(
            go.Scatter(
                x=pc_names,
                y=cumulative_ratios,
                name='Cumulative',
                mode='lines+markers',
                line=dict(color='#ff7f0e', width=2),
                marker=dict(size=8),
                hovertemplate='Cumulative: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=True
        )
        
        # Update layout
        fig.update_layout(
            height=350,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=10, b=10)
        )
        fig.update_xaxes(title_text="Principal Component")
        fig.update_yaxes(title_text="Variance Explained (%)", secondary_y=False)
        fig.update_yaxes(title_text="Cumulative (%)", secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True, key="pca_variance_chart")
        
        # Summary metrics
        st.caption(f"**Total Variance Explained:** {cumulative_variance * 100:.1f}%")
        st.caption(f"**Components Retained:** {len(variance)}")
    
    with col2:
        st.markdown("### Narrative Feed")
        
        if narratives:
            for idx, narrative in enumerate(narratives):
                with st.expander(f"PC{idx + 1} Interpretation", expanded=(idx == 0)):
                    st.markdown(narrative)
        else:
            st.info("No narrative interpretations available")
    
    # Loadings table with CSV download
    st.divider()
    st.markdown("### Feature Loadings")
    
    if loadings:
        selected_pc = st.selectbox(
            "Select Component",
            options=list(loadings.keys()),
            key="pca_loadings_select"
        )
        
        if selected_pc:
            pc_loadings = loadings[selected_pc]
            
            # Convert to DataFrame
            loadings_df = pd.DataFrame(pc_loadings, columns=['Feature', 'Loading'])
            
            st.dataframe(
                loadings_df,
                use_container_width=True,
                hide_index=True,
                height=300
            )
            
            # CSV download button
            csv_buffer = io.StringIO()
            loadings_df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label=f"📥 Download {selected_pc} Loadings (CSV)",
                data=csv_data,
                file_name=f"{selected_pc}_loadings.csv",
                mime="text/csv",
                key=f"download_loadings_{selected_pc}"
            )
    else:
        st.info("No loadings data available")
    
    # Compare Components toggle
    st.divider()
    compare_components = st.checkbox("🔍 Compare Components", key="compare_pcs")
    
    if compare_components and len(loadings) > 1:
        st.markdown("### Component Comparison")
        
        selected_pcs = st.multiselect(
            "Select components to compare",
            options=list(loadings.keys()),
            default=list(loadings.keys())[:min(3, len(loadings))],
            key="compare_pcs_select"
        )
        
        if len(selected_pcs) > 1:
            # Build radar chart
            # Collect all features across selected PCs
            all_features = set()
            for pc in selected_pcs:
                all_features.update([feat for feat, _ in loadings[pc]])
            all_features = sorted(all_features)[:10]  # Limit to top 10 for readability
            
            # Build data structure for radar chart
            radar_data = []
            for pc in selected_pcs:
                pc_dict = {feat: load for feat, load in loadings[pc]}
                values = [pc_dict.get(feat, 0.0) for feat in all_features]
                
                radar_data.append(
                    go.Scatterpolar(
                        r=values,
                        theta=all_features,
                        fill='toself',
                        name=pc
                    )
                )
            
            fig_radar = go.Figure(data=radar_data)
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[-1, 1])),
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig_radar, use_container_width=True, key="pca_radar_chart")
        elif len(selected_pcs) == 1:
            st.info("Select at least 2 components for comparison")
    elif compare_components:
        st.info("Need at least 2 components for comparison")


def render_pca_legacy(pca_components: List[Dict[str, Any]]) -> None:
    """Render PCA component information (legacy format).
    
    Args:
        pca_components: List of PCA component dictionaries from backend with:
            - component: int
            - explained_variance_ratio: float
            - top_contributors: list of {feature: str, loading: float}
    """
    st.subheader("📊 PCA Components")
    
    if not pca_components:
        st.info("PCA data not available")
        return
    
    # Display variance explained
    st.markdown("**Explained Variance by Component:**")
    
    variance_data = []
    for comp in pca_components:
        variance_data.append({
            'Component': f"PC{comp['component']}",
            'Variance Explained': f"{comp['explained_variance_ratio'] * 100:.2f}%"
        })
    
    if variance_data:
        df_variance = pd.DataFrame(variance_data)
        st.dataframe(df_variance, use_container_width=True, hide_index=True)
    
    # Display top contributors for each component
    st.divider()
    st.markdown("**Top Contributing Features:**")
    
    selected_component = st.selectbox(
        "Select Component",
        options=[f"PC{comp['component']}" for comp in pca_components],
        key="pca_component_select"
    )
    
    if selected_component:
        comp_idx = int(selected_component.replace('PC', '')) - 1
        if comp_idx < len(pca_components):
            component = pca_components[comp_idx]
            contributors = component.get('top_contributors', [])
            
            if contributors:
                contrib_data = pd.DataFrame([
                    {
                        'Feature': contrib['feature'],
                        'Loading': f"{contrib['loading']:.4f}",
                        'Abs Loading': abs(contrib['loading'])
                    }
                    for contrib in contributors
                ])
                
                # Sort by absolute loading
                contrib_data = contrib_data.sort_values('Abs Loading', ascending=False)
                contrib_data = contrib_data.drop('Abs Loading', axis=1)
                
                st.dataframe(contrib_data, use_container_width=True, hide_index=True)
                
                # Create bar chart of loadings
                fig = go.Figure(data=[
                    go.Bar(
                        x=[c['loading'] for c in contributors],
                        y=[c['feature'] for c in contributors],
                        orientation='h',
                        marker=dict(
                            color=[c['loading'] for c in contributors],
                            colorscale='RdBu',
                            cmid=0
                        )
                    )
                ])
                
                fig.update_layout(
                    title=f"Feature Loadings for {selected_component}",
                    xaxis_title="Loading",
                    yaxis_title="Feature",
                    height=400,
                    yaxis={'categoryorder': 'total ascending'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No contributor data available for this component")
    
    # Summary stats
    with st.expander("📊 Summary"):
        total_variance = sum(comp['explained_variance_ratio'] for comp in pca_components)
        st.metric("Total Variance Explained", f"{total_variance * 100:.2f}%")
        st.metric("Number of Components", len(pca_components))


# ==============================================================================
# CHANGE-POINTS TAB
# ==============================================================================

def render_change_points_enhanced(reports: List[Dict[str, Any]]) -> None:
    """Render enhanced change-point detection with segment summaries.
    
    Implements DataUnderstanding_v2.md Section 2.3 specification with:
    - Time-series visualization with vertical change-point markers
    - Segment summary table with quality flags
    - Context chips for cluster shifts and batch metadata
    - Drill-down navigation via marker clicks
    
    Args:
        reports: List of ChangePointReportModel dictionaries with:
            - column: str
            - method: str ('pelt' or 'cusum')
            - n: int (number of change points)
            - indices: list[int] (sorted change-point locations)
            - segments: list[SegmentSummary] (statistical summaries)
            - strength: list[float] (test statistics)
            - context: list[ChangePointContext] (temporal/cluster/batch info)
            - flags: list[str] (quality flags)
    """
    st.subheader("📈 Change-Point Detection - Enhanced View")
    
    if not reports:
        st.info("No change-point reports available")
        return
    
    # Column selector
    columns = [r['column'] for r in reports]
    selected_column = st.selectbox(
        "Select column",
        options=columns,
        key="changepoint_col_enhanced"
    )
    
    # Find selected report
    report = next((r for r in reports if r['column'] == selected_column), None)
    if not report:
        st.warning("Report not found for selected column")
        return
    
    method = report.get('method', 'unknown')
    n_changepoints = report.get('n', 0)
    indices = report.get('indices', [])
    segments = report.get('segments', [])
    strengths = report.get('strength', [])
    contexts = report.get('context', [])
    flags = report.get('flags', [])
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Change Points Detected", n_changepoints)
    with col2:
        st.metric("Detection Method", method.upper())
    with col3:
        st.metric("Segments", len(segments))
    
    # Quality flags
    if flags:
        st.markdown("**Quality Flags:**")
        render_flags_inline(flags)
        st.divider()
    
    # Time-series visualization with markers
    if indices:
        st.markdown("### Time-Series with Change Points")
        
        # Note: Actual data not available in report, so we create a placeholder visualization
        # In production, backend should include segment data or frontend should fetch it
        st.info("📊 Time-series chart would display here with vertical markers at detected change points. "
                "Requires segment data from backend.")
        
        # Create simple marker visualization
        fig = go.Figure()
        
        # Color by strength bucket (if available)
        if strengths and len(strengths) == len(indices):
            # Normalize strengths for coloring
            max_strength = max(strengths) if strengths else 1.0
            colors = []
            for s in strengths:
                if s >= 0.7 * max_strength:
                    colors.append('red')  # High
                elif s >= 0.4 * max_strength:
                    colors.append('orange')  # Medium
                else:
                    colors.append('yellow')  # Low
        else:
            colors = ['red'] * len(indices)
        
        fig.add_trace(go.Scatter(
            x=indices,
            y=[1] * len(indices),
            mode='markers+text',
            marker=dict(
                size=15,
                color=colors,
                symbol='line-ns',
                line=dict(width=2, color='DarkSlateGrey')
            ),
            text=[f"CP{i+1}" for i in range(len(indices))],
            textposition="top center",
            name='Change Points',
            hovertemplate='Index: %{x}<br>Strength: %{customdata:.3f}<extra></extra>',
            customdata=strengths if strengths else [0]*len(indices)
        ))
        
        fig.update_layout(
            title=f"Change Point Locations in {selected_column}",
            xaxis_title="Data Index (or Time)",
            yaxis_visible=False,
            height=250,
            showlegend=False,
            hovermode='closest'
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"changepoints_viz_{selected_column}")
    
    # Segment summary table
    if segments:
        st.markdown("### Segment Summaries")
        
        total_segment_n = sum(s.get('n', 0) for s in segments)
        total_segment_n = total_segment_n if total_segment_n > 0 else 1

        segment_data = []
        for idx, seg in enumerate(segments):
            start = seg.get('start', 0)
            end = seg.get('end', 0)
            mean = seg.get('mean', 0.0)
            std = seg.get('std', 0.0)
            n = seg.get('n', 0)
            
            # Highlight segments with insufficient data
            highlight = "⚠️ " if n < 30 else ""
            
            segment_data.append({
                'Segment': f"{highlight}#{idx + 1}",
                'Start': start,
                'End': end,
                'Mean': f"{mean:.3f}",
                'Std Dev': f"{std:.3f}",
                'N': n,
                'Pct': f"{(n / total_segment_n) * 100:.1f}%"
            })
        
        df_segments = pd.DataFrame(segment_data)
        st.dataframe(
            df_segments,
            use_container_width=True,
            hide_index=True,
            height=300
        )
        
        st.caption("⚠️ = Segment size below recommended threshold")
    
    # Context chips
    if contexts:
        st.markdown("### Context Information")
        
        for idx, ctx in enumerate(contexts):
            index = ctx.get('index', 0)
            timestamp = ctx.get('timestamp')
            cluster_shift = ctx.get('cluster_shift')
            batch_info = ctx.get('batch_info')
            
            with st.expander(f"Change Point #{idx + 1} @ Index {index}"):
                if timestamp:
                    st.markdown(f"**Timestamp:** {timestamp}")
                
                if cluster_shift:
                    before = cluster_shift.get('before')
                    after = cluster_shift.get('after')
                    if before is not None and after is not None:
                        st.markdown(f"**Cluster Shift:** {before} → {after}")
                
                if batch_info:
                    st.markdown(f"**Batch Info:** {batch_info}")
                
                if not timestamp and not cluster_shift and not batch_info:
                    st.info("No additional context available")
    
    # Drill-down guidance
    st.divider()
    with st.expander("💡 Usage Guide"):
        st.markdown("""
        **How to interpret change points:**
        
        - **High Strength (Red):** Strong evidence of regime change
        - **Medium Strength (Orange):** Moderate evidence, verify with domain knowledge
        - **Low Strength (Yellow):** Weak signal, may be noise
        
        **Segment Analysis:**
        - Compare mean and std dev across segments to understand shifts
        - Small segments (⚠️) may not be statistically reliable
        - Use percentage column to understand relative segment sizes
        
        **Context Clues:**
        - Cluster shifts indicate grouping changes coinciding with change points
        - Batch metadata helps correlate with production events
        """)


def render_change_points_legacy(change_data: List[Dict[str, Any]]) -> None:
    """Render change-point detection information (legacy format).
    
    Args:
        change_data: List of change-point detection results from backend with:
            - column: str
            - method: str
            - locations: list of int (indices where changes detected)
    """
    st.subheader("📈 Change-Point Detection")
    
    if not change_data:
        st.info("Change-point data not available")
        return
    
    # Group by column
    changes_by_column = {}
    for change in change_data:
        col = change['column']
        if col not in changes_by_column:
            changes_by_column[col] = []
        changes_by_column[col].append(change)
    
    # Column selector
    selected_col = st.selectbox(
        "Select column",
        options=list(changes_by_column.keys()),
        key="changepoint_col"
    )
    
    if selected_col:
        col_changes = changes_by_column[selected_col]
        
        # Display change points for this column
        for change in col_changes:
            method = change.get('method', 'Unknown')
            locations = change.get('locations', [])
            
            st.markdown(f"**Method:** {method}")
            
            if locations:
                st.markdown(f"**Detected {len(locations)} change point(s) at indices:**")
                
                # Create DataFrame for better display
                df = pd.DataFrame({
                    'Change Point Index': locations
                })
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Simple visualization of change point locations
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=locations,
                    y=[1] * len(locations),
                    mode='markers',
                    marker=dict(size=12, color='red', symbol='line-ns'),
                    name='Change Points',
                    hovertemplate='Index: %{x}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f"Change Point Locations in {selected_col}",
                    xaxis_title="Data Index",
                    yaxis_visible=False,
                    height=200,
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No change points detected using {method} method")
            
            st.divider()
    
    # Summary stats
    with st.expander("📊 Summary"):
        total_changes = sum(len(change.get('locations', [])) for change in change_data)
        st.metric("Total Change Points Detected", total_changes)
        st.metric("Columns Analyzed", len(changes_by_column))


# ==============================================================================
# CLUSTERS TAB
# ==============================================================================

def render_clusters_enhanced(cluster_profile: Optional[Dict[str, Any]]) -> None:
    """Render enhanced cluster analysis with deep-dive profiling.
    
    Implements DataUnderstanding_v2.md Section 2.4 specification with:
    - Cluster size distribution (stacked bar or pie chart)
    - Medoid sample table with pagination
    - Feature differences accordion (ANOVA, effect sizes, importance)
    - Cluster timeline view (when temporal data present)
    - Export cluster assignments button
    
    Args:
        cluster_profile: ClusterProfileModel dictionary with:
            - method: str ('kmeans' or 'hierarchical')
            - k: int (number of clusters)
            - sizes: list[dict] with {'id': int, 'n': int, 'pct': float}
            - top_diff_features: list[dict] (ANOVA results)
            - feature_importance: list[dict] (tree-based importance)
            - medoids: dict[str, list[int]] (cluster_id -> sample indices)
            - per_feature_stats: dict (cluster stats by feature)
            - by_time: Optional[list[dict]] (temporal distribution)
    """
    st.subheader("🔵 Clusters - Deep Dive")
    
    if not cluster_profile:
        st.info("Cluster profile data not available")
        return
    
    method = cluster_profile.get('method', 'unknown')
    k = cluster_profile.get('k', 0)
    sizes = cluster_profile.get('sizes', [])
    top_diff_features = cluster_profile.get('top_diff_features', [])
    feature_importance = cluster_profile.get('feature_importance', [])
    medoids = cluster_profile.get('medoids', {})
    per_feature_stats = cluster_profile.get('per_feature_stats', {})
    by_time = cluster_profile.get('by_time')
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Clustering Method", method.upper())
    with col2:
        st.metric("Number of Clusters", k)
    with col3:
        total_obs = sum(s.get('n', 0) for s in sizes)
        st.metric("Total Observations", total_obs)
    
    st.divider()
    
    # Cluster size distribution
    if sizes:
        st.markdown("### Cluster Size Distribution")
        
        col_chart1, col_chart2 = st.columns([1, 1])
        
        with col_chart1:
            # Stacked bar chart
            df_sizes = pd.DataFrame(sizes)
            if 'id' in df_sizes.columns:
                df_sizes['Cluster'] = df_sizes['id'].astype(str)
            
            if 'pct' in df_sizes.columns:
                pct_text = df_sizes['pct'].apply(lambda x: f"{x * 100:.1f}%")
            else:
                pct_text = None

            fig_bar = go.Figure(data=[
                go.Bar(
                    x=df_sizes.get('Cluster', df_sizes.get('id')),
                    y=df_sizes.get('n', []),
                    text=pct_text,
                    textposition='auto',
                    marker_color='#1f77b4',
                    hovertemplate='Cluster %{x}<br>Size: %{y}<extra></extra>'
                )
            ])
            
            fig_bar.update_layout(
                title="Cluster Sizes",
                xaxis_title="Cluster ID",
                yaxis_title="Number of Samples",
                height=300
            )
            
            st.plotly_chart(fig_bar, use_container_width=True, key="cluster_bar")
        
        with col_chart2:
            # Pie chart
            fig_pie = px.pie(
                df_sizes,
                values='n',
                names='Cluster' if 'Cluster' in df_sizes.columns else 'id',
                title="Cluster Proportions"
            )
            fig_pie.update_layout(height=300)
            
            st.plotly_chart(fig_pie, use_container_width=True, key="cluster_pie")
    
    # Medoid sample table
    if medoids:
        st.divider()
        st.markdown("### Representative Samples (Medoids)")
        
        # Pagination controls
        items_per_page = 5
        total_clusters = len(medoids)
        total_pages = (total_clusters + items_per_page - 1) // items_per_page
        
        page = st.selectbox(
            "Page",
            options=list(range(1, total_pages + 1)),
            key="medoids_page"
        )
        
        # Display medoids for current page
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_clusters)
        
        def _cluster_sort_key(cluster_id: Any) -> tuple:
            """Best-effort sorting that handles numeric and string cluster IDs."""
            if isinstance(cluster_id, (int, float)):
                return (0, cluster_id)

            try:
                return (0, int(cluster_id))
            except (TypeError, ValueError):
                return (1, str(cluster_id))

        cluster_ids = sorted(medoids.keys(), key=_cluster_sort_key)
        page_clusters = cluster_ids[start_idx:end_idx]
        
        medoid_data = []
        for cluster_id in page_clusters:
            indices = medoids[cluster_id]
            medoid_data.append({
                'Cluster ID': cluster_id,
                'Medoid Indices': ', '.join(map(str, indices[:5])),  # Show first 5
                'Count': len(indices)
            })
        
        df_medoids = pd.DataFrame(medoid_data)
        st.dataframe(df_medoids, use_container_width=True, hide_index=True)
        
        st.caption(f"Showing clusters {start_idx+1}-{end_idx} of {total_clusters}")
    
    # Feature differences accordion
    if top_diff_features:
        st.divider()
        st.markdown("### Feature Differences Between Clusters")
        
        with st.expander("📊 ANOVA Results (Top Discriminating Features)"):
            diff_data = []
            for feat_result in top_diff_features[:10]:  # Top 10
                feature = feat_result.get('feature', '')
                p_value = feat_result.get('p', 1.0)
                f_stat = feat_result.get('f_stat', 0.0)
                eta_squared = feat_result.get('eta_squared', 0.0)
                
                # Effect size interpretation
                if eta_squared >= 0.14:
                    effect = "Large"
                elif eta_squared >= 0.06:
                    effect = "Medium"
                else:
                    effect = "Small"
                
                diff_data.append({
                    'Feature': feature,
                    'F-statistic': f"{f_stat:.2f}",
                    'p-value': f"{p_value:.4f}",
                    'η² (Effect)': f"{eta_squared:.3f} ({effect})"
                })
            
            df_diff = pd.DataFrame(diff_data)
            st.dataframe(df_diff, use_container_width=True, hide_index=True)
            
            st.caption("**Interpretation:** Lower p-values and higher η² indicate features that differ significantly between clusters.")
    
    if feature_importance:
        with st.expander("🌳 Tree-Based Feature Importance"):
            imp_data = []
            for imp_result in feature_importance[:10]:  # Top 10
                feature = imp_result.get('feature', '')
                importance = imp_result.get('importance', 0.0)
                
                imp_data.append({
                    'Feature': feature,
                    'Importance': f"{importance:.3f}",
                    'Importance Bar': importance  # For visual
                })
            
            df_imp = pd.DataFrame(imp_data)
            
            # Create horizontal bar chart
            fig_imp = go.Figure(data=[
                go.Bar(
                    y=df_imp['Feature'],
                    x=df_imp['Importance Bar'],
                    orientation='h',
                    marker_color='#2ca02c',
                    text=df_imp['Importance'],
                    textposition='auto'
                )
            ])
            
            fig_imp.update_layout(
                title="Predictive Features for Cluster Assignment",
                xaxis_title="Importance",
                yaxis_title="Feature",
                height=400,
                yaxis={'categoryorder': 'total ascending'}
            )
            
            st.plotly_chart(fig_imp, use_container_width=True, key="feature_importance")
            
            st.caption("**Interpretation:** Features with higher importance are most useful for distinguishing clusters.")
    
    # Cluster timeline view
    if by_time:
        st.divider()
        st.markdown("### Cluster Evolution Over Time")
        
        # Prepare data for stacked area chart
        df_time = pd.DataFrame(by_time)
        
        if not df_time.empty and 'window' in df_time.columns and 'cluster' in df_time.columns:
            # Pivot for stacked area
            df_pivot = df_time.pivot_table(
                index='window',
                columns='cluster',
                values='pct',
                fill_value=0
            )
            
            # Create stacked area chart
            fig_time = go.Figure()
            
            colors = px.colors.qualitative.Plotly
            for idx, cluster_id in enumerate(df_pivot.columns):
                fig_time.add_trace(go.Scatter(
                    x=df_pivot.index,
                    y=df_pivot[cluster_id],
                    mode='lines',
                    stackgroup='one',
                    name=f'Cluster {cluster_id}',
                    fillcolor=colors[idx % len(colors)],
                    hovertemplate=f'Cluster {cluster_id}<br>Proportion: %{{y:.1%}}<extra></extra>'
                ))
            
            fig_time.update_layout(
                title="Cluster Proportions Over Time",
                xaxis_title="Time Window",
                yaxis_title="Proportion",
                yaxis_tickformat='.0%',
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_time, use_container_width=True, key="cluster_timeline")
            
            st.caption("**Interpretation:** Visualizes how cluster membership changes over time periods.")
        else:
            st.info("Temporal data structure not recognized")
    
    # Export button
    st.divider()
    col_export1, col_export2 = st.columns([1, 3])
    with col_export1:
        if st.button("📥 Export Cluster Assignments", key="export_clusters"):
            st.info("Export functionality requires backend endpoint. Feature placeholder implemented.")
    
    with col_export2:
        st.caption("Export will download a CSV file with sample indices and assigned cluster IDs")


def render_clusters_legacy(cluster_data: List[Dict[str, Any]]) -> None:
    """Render cluster analysis summary (legacy format).
    
    Args:
        cluster_data: List of cluster summaries from backend with:
            - method: str (e.g., "kmeans", "hierarchical")
            - cluster_sizes: dict mapping cluster_id to size
    """
    st.subheader("🔵 Cluster Analysis")
    
    if not cluster_data:
        st.info("Cluster data not available")
        return
    
    # Display each clustering result
    for cluster_result in cluster_data:
        method = cluster_result.get('method', 'Unknown')
        cluster_sizes = cluster_result.get('cluster_sizes', {})
        
        st.markdown(f"**Method:** {method}")
        
        if cluster_sizes:
            # Convert to DataFrame for display
            df = pd.DataFrame([
                {
                    'Cluster ID': cluster_id,
                    'Size': size,
                    'Percentage': f"{(size / sum(cluster_sizes.values())) * 100:.1f}%"
                }
                for cluster_id, size in cluster_sizes.items()
            ])
            
            # Sort by cluster ID
            df = df.sort_values('Cluster ID')
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            with col2:
                # Pie chart of cluster distribution
                fig = px.pie(
                    df,
                    values='Size',
                    names='Cluster ID',
                    title=f"Cluster Distribution ({method})"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Summary metrics
            st.caption(f"**Total clusters:** {len(cluster_sizes)} | **Total observations:** {sum(cluster_sizes.values())}")
        else:
            st.info(f"No cluster size data available for {method}")
        
        st.divider()
    
    # Overall summary
    with st.expander("📊 Summary"):
        st.metric("Clustering Methods Used", len(cluster_data))
