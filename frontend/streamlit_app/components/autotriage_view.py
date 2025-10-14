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
            - suspicion_rankings: list of column suspicions
            - pca_results: dict with PCA data
            - change_points: dict with change-point data
            - cluster_summary: dict with clustering data
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
        render_pca_biplot(result_data.get('pca_results', {}))
    
    with tab3:
        render_change_points(result_data.get('change_points', {}))
    
    with tab4:
        render_clusters(result_data.get('cluster_summary', {}))


def render_suspicion_rankings(rankings: List[Dict[str, Any]]) -> None:
    """Render suspicion rankings table with scoring breakdown.
    
    Args:
        rankings: List of suspicion ranking dictionaries
    """
    st.subheader("Column Suspicion Rankings")
    
    if not rankings:
        st.info("No suspicion rankings available")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(rankings)
    
    # Sort by total score
    df = df.sort_values('total_score', ascending=False)
    
    # Create severity categories
    def categorize_score(score):
        if score >= 70:
            return "🔴 High"
        elif score >= 40:
            return "🟡 Medium"
        else:
            return "🟢 Low"
    
    df['Severity'] = df['total_score'].apply(categorize_score)
    
    # Format display columns
    display_df = pd.DataFrame({
        'Rank': range(1, len(df) + 1),
        'Column': df['column_name'],
        'Total Score': df['total_score'].apply(lambda x: f"{x:.1f}"),
        'Severity': df['Severity'],
        'Missing %': df.get('missing_pct', pd.Series([0]*len(df))).apply(lambda x: f"{x:.1f}%"),
        'Outliers': df.get('outlier_count', pd.Series([0]*len(df))),
        'Flags': df.get('flag_count', pd.Series([0]*len(df)))
    })
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Scoring breakdown for selected column
    st.divider()
    st.markdown("#### Scoring Breakdown")
    
    selected_col = st.selectbox(
        "Select column for detailed breakdown",
        options=df['column_name'].tolist(),
        key="suspicion_detail"
    )
    
    if selected_col:
        row = df[df['column_name'] == selected_col].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Score Components:**")
            
            components = {
                'Missing Data': row.get('missing_score', 0),
                'Outliers': row.get('outlier_score', 0),
                'Distribution': row.get('distribution_score', 0),
                'Correlation': row.get('correlation_score', 0),
                'Pattern': row.get('pattern_score', 0)
            }
            
            for component, score in components.items():
                st.text(f"{component}: {score:.1f}")
        
        with col2:
            # Create pie chart of score components
            fig = go.Figure(data=[go.Pie(
                labels=list(components.keys()),
                values=list(components.values()),
                hole=0.3
            )])
            
            fig.update_layout(
                title=f"Score Components for {selected_col}",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Summary statistics
    with st.expander("📊 Summary"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_suspicion = (df['total_score'] >= 70).sum()
            st.metric("High Suspicion", high_suspicion)
        
        with col2:
            medium_suspicion = ((df['total_score'] >= 40) & (df['total_score'] < 70)).sum()
            st.metric("Medium Suspicion", medium_suspicion)
        
        with col3:
            low_suspicion = (df['total_score'] < 40).sum()
            st.metric("Low Suspicion", low_suspicion)


def render_pca_biplot(pca_data: Dict[str, Any]) -> None:
    """Render PCA biplot showing observations and loadings.
    
    Args:
        pca_data: Dictionary with PCA results
    """
    st.subheader("PCA Biplot")
    
    if not pca_data or 'scores' not in pca_data:
        st.info("PCA data not available")
        return
    
    scores = np.array(pca_data['scores'])
    loadings = np.array(pca_data.get('loadings', []))
    explained_variance = pca_data.get('explained_variance', [])
    feature_names = pca_data.get('feature_names', [])
    
    if len(scores) == 0:
        st.info("No PCA scores available")
        return
    
    # Component selection
    n_components = scores.shape[1] if len(scores.shape) > 1 else 1
    
    if n_components < 2:
        st.warning("Need at least 2 principal components for biplot")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        pc_x = st.selectbox("X-axis", options=range(1, n_components + 1), index=0, key="pca_x")
    
    with col2:
        pc_y = st.selectbox("Y-axis", options=range(1, n_components + 1), index=1 if n_components > 1 else 0, key="pca_y")
    
    # Extract selected components (convert to 0-indexed)
    pc_x_idx = pc_x - 1
    pc_y_idx = pc_y - 1
    
    x_scores = scores[:, pc_x_idx]
    y_scores = scores[:, pc_y_idx]
    
    # Create figure
    fig = go.Figure()
    
    # Add observation points
    fig.add_trace(go.Scatter(
        x=x_scores,
        y=y_scores,
        mode='markers',
        marker=dict(size=6, color='blue', opacity=0.6),
        name='Observations',
        hovertemplate='Obs %{pointNumber}<br>PC%{x}: %{x:.3f}<br>PC%{y}: %{y:.3f}<extra></extra>'
    ))
    
    # Add loading vectors if available
    if len(loadings) > 0 and len(feature_names) > 0:
        x_loadings = loadings[:, pc_x_idx]
        y_loadings = loadings[:, pc_y_idx]
        
        # Scale loadings for visibility
        max_score = max(abs(x_scores).max(), abs(y_scores).max())
        max_loading = max(abs(x_loadings).max(), abs(y_loadings).max())
        scale = max_score / max_loading * 0.8 if max_loading > 0 else 1
        
        for i, name in enumerate(feature_names):
            fig.add_annotation(
                x=x_loadings[i] * scale,
                y=y_loadings[i] * scale,
                ax=0,
                ay=0,
                xref='x',
                yref='y',
                axref='x',
                ayref='y',
                text=name,
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor='red',
                font=dict(size=10, color='red')
            )
    
    # Add reference lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Update layout
    x_var = explained_variance[pc_x_idx] if pc_x_idx < len(explained_variance) else 0
    y_var = explained_variance[pc_y_idx] if pc_y_idx < len(explained_variance) else 0
    
    fig.update_layout(
        title="PCA Biplot",
        xaxis_title=f"PC{pc_x} ({x_var:.1f}% variance)",
        yaxis_title=f"PC{pc_y} ({y_var:.1f}% variance)",
        height=600,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Explained variance table
    if explained_variance:
        with st.expander("📊 Explained Variance"):
            variance_df = pd.DataFrame({
                'Component': [f"PC{i+1}" for i in range(len(explained_variance))],
                'Variance %': explained_variance,
                'Cumulative %': np.cumsum(explained_variance)
            })
            
            st.dataframe(variance_df, use_container_width=True, hide_index=True)


def render_change_points(change_data: Dict[str, Any]) -> None:
    """Render change-point detection charts.
    
    Args:
        change_data: Dictionary with change-point detection results
    """
    st.subheader("Change-Point Detection")
    
    if not change_data:
        st.info("Change-point data not available")
        return
    
    detections = change_data.get('detections', [])
    
    if not detections:
        st.info("No change points detected")
        return
    
    # Column selector
    columns = list(set(d['column'] for d in detections))
    selected_col = st.selectbox(
        "Select column",
        options=columns,
        key="changepoint_col"
    )
    
    # Filter detections for selected column
    col_detections = [d for d in detections if d['column'] == selected_col]
    
    if not col_detections:
        st.info(f"No change points for {selected_col}")
        return
    
    # Get time series data
    time_series = change_data.get('time_series', {}).get(selected_col, [])
    
    if not time_series:
        st.warning("Time series data not available")
        return
    
    # Create time series plot
    fig = go.Figure()
    
    # Add time series line
    indices = list(range(len(time_series)))
    
    fig.add_trace(go.Scatter(
        x=indices,
        y=time_series,
        mode='lines',
        line=dict(color='blue'),
        name='Values'
    ))
    
    # Add change points
    for detection in col_detections:
        idx = detection.get('index', 0)
        severity = detection.get('severity', 'info')
        
        color = {
            'error': 'red',
            'warning': 'orange',
            'info': 'yellow'
        }.get(severity, 'yellow')
        
        fig.add_vline(
            x=idx,
            line_dash="dash",
            line_color=color,
            annotation_text=f"CP (p={detection.get('p_value', 0):.3f})",
            annotation_position="top"
        )
    
    fig.update_layout(
        title=f"Change Points in {selected_col}",
        xaxis_title="Index",
        yaxis_title="Value",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Change point details table
    st.markdown("#### Detected Change Points")
    
    details_df = pd.DataFrame([{
        'Index': d.get('index', 0),
        'P-Value': f"{d.get('p_value', 0):.4f}",
        'Severity': d.get('severity', 'info'),
        'Mean Before': f"{d.get('mean_before', 0):.3f}",
        'Mean After': f"{d.get('mean_after', 0):.3f}",
        'Change %': f"{d.get('change_pct', 0):.1f}%"
    } for d in col_detections])
    
    st.dataframe(details_df, use_container_width=True, hide_index=True)


def render_clusters(cluster_data: Dict[str, Any]) -> None:
    """Render cluster visualization and summary.
    
    Args:
        cluster_data: Dictionary with clustering results
    """
    st.subheader("Cluster Analysis")
    
    if not cluster_data:
        st.info("Cluster data not available")
        return
    
    labels = cluster_data.get('labels', [])
    centroids = cluster_data.get('centroids', [])
    
    if not labels:
        st.info("No cluster assignments available")
        return
    
    # Get embedding coordinates (from PCA or other dimensionality reduction)
    coords = cluster_data.get('coordinates', [])
    
    if not coords or len(coords) == 0:
        st.warning("Coordinate data not available for visualization")
        return
    
    coords = np.array(coords)
    labels = np.array(labels)
    
    # Create scatter plot
    fig = px.scatter(
        x=coords[:, 0],
        y=coords[:, 1],
        color=labels.astype(str),
        title="Cluster Visualization",
        labels={'x': 'Dimension 1', 'y': 'Dimension 2', 'color': 'Cluster'},
        height=500
    )
    
    # Add centroids if available
    if centroids:
        centroids = np.array(centroids)
        fig.add_trace(go.Scatter(
            x=centroids[:, 0],
            y=centroids[:, 1],
            mode='markers',
            marker=dict(
                size=15,
                color='black',
                symbol='x',
                line=dict(width=2, color='white')
            ),
            name='Centroids',
            showlegend=True
        ))
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Cluster summary
    st.markdown("#### Cluster Summary")
    
    unique_labels = np.unique(labels)
    summary_data = []
    
    for label in unique_labels:
        mask = labels == label
        count = mask.sum()
        pct = (count / len(labels)) * 100
        
        summary_data.append({
            'Cluster': f"Cluster {label}",
            'Size': count,
            'Percentage': f"{pct:.1f}%"
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    with col2:
        # Pie chart of cluster sizes
        fig_pie = px.pie(
            summary_df,
            values='Size',
            names='Cluster',
            title="Cluster Distribution"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Silhouette score if available
    silhouette = cluster_data.get('silhouette_score')
    if silhouette is not None:
        st.metric("Silhouette Score", f"{silhouette:.3f}")
        st.caption("Range: [-1, 1]. Higher is better. >0.5 indicates good clustering.")
