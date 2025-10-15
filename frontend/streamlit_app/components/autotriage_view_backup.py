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

# Import navigation and state management
from utils.autotriage_state import (
    get_autotriage_state,
    set_active_autotriage_tab,
    render_navigation_breadcrumb,
    get_navigation_from_link,
)
from utils.navigation import sync_state_from_url, set_query_params
from components.confidence_flags import render_flags_inline


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
    
    # Map state.active_tab to tab index
    tab_map = {"suspicion": 0, "pca": 1, "changepoints": 2, "clusters": 3}
    active_idx = tab_map.get(state.active_tab, 0)
    
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


def render_pca_biplot(pca_components: List[Dict[str, Any]]) -> None:
    """Render PCA component information and top contributors.
    
    Args:
        pca_components: List of PCA component dictionaries from backend with:
            - component: int
            - explained_variance_ratio: float
            - top_contributors: list of {feature: str, loading: float}
    """
    st.subheader("PCA Components")
    
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


def render_change_points(change_data: List[Dict[str, Any]]) -> None:
    """Render change-point detection information.
    
    Args:
        change_data: List of change-point detection results from backend with:
            - column: str
            - method: str
            - locations: list of int (indices where changes detected)
    """
    st.subheader("Change-Point Detection")
    
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


def render_clusters(cluster_data: List[Dict[str, Any]]) -> None:
    """Render cluster analysis summary.
    
    Args:
        cluster_data: List of cluster summaries from backend with:
            - method: str (e.g., "kmeans", "hierarchical")
            - cluster_sizes: dict mapping cluster_id to size
    """
    st.subheader("Cluster Analysis")
    
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
