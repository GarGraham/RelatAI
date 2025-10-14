"""Auto-triage analysis visualization components.

Provides suspicion rankings, PCA biplot, change-point detection charts,
and cluster visualizations for automated quality triage results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
import numpy as np


def render_autotriage_results(result_data: Dict[str, Any]) -> None:
    """Render complete auto-triage analysis results with all visualizations.
    
    Args:
        result_data: Auto-triage result dictionary containing:
            - suspicion_rankings: list of ranked insights
            - pca_components: list of PCA component data
            - change_points: list of change-point detections
            - clusters: list of cluster summaries
            - residual_forensics: list of residual analysis results
    """
    if not result_data:
        st.warning("No auto-triage data available")
        return
    
    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Suspicion Rankings",
        "📊 PCA Biplot",
        "📈 Change Points",
        "🔵 Clusters"
    ])
    
    with tab1:
        render_suspicion_rankings(result_data.get('suspicion_rankings', []))
    
    with tab2:
        render_pca_biplot(result_data.get('pca_components', []))
    
    with tab3:
        render_change_points(result_data.get('change_points', []))
    
    with tab4:
        render_clusters(result_data.get('clusters', []))


def render_suspicion_rankings(rankings: List[Dict[str, Any]]) -> None:
    """Render suspicion rankings table.
    
    Args:
        rankings: List of RankedInsightModel dictionaries from backend with:
            - label: str (column or feature name)
            - score: float (0.0 to 1.0)
            - drivers: list of str (reasons for suspicion)
            - category: str
            - method: str (optional)
    """
    st.subheader("Suspicion Rankings")
    
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
