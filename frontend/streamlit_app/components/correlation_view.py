"""Correlation analysis visualization components.

Provides ranked table, heatmap, and network graph visualizations
for pairwise correlation analysis results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
import numpy as np


def render_correlation_results(result_data: Dict[str, Any]) -> None:
    """Render complete correlation analysis results with all visualizations.
    
    Args:
        result_data: Correlation result dictionary containing:
            - correlation_table: dict with 'records' list
            - quality_flags: list of flags
            - generated_at: timestamp
    """
    if not result_data or "correlation_table" not in result_data:
        st.warning("No correlation data available")
        return
    
    table = result_data["correlation_table"]
    records = table.get("records", [])
    
    if not records:
        st.info("No correlation records found")
        return
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs([
        "📊 Ranked Table",
        "🔥 Heatmap",
        "🕸️ Network Graph"
    ])
    
    with tab1:
        render_correlation_table(records)
    
    with tab2:
        render_correlation_heatmap(records)
    
    with tab3:
        render_correlation_network(records)


def render_correlation_table(records: List[Dict[str, Any]]) -> None:
    """Render sortable, paginated correlation table.
    
    Args:
        records: List of correlation record dictionaries
    """
    st.subheader("Ranked Correlations")
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Format variables column
    df['Variable 1'] = df['variables'].apply(lambda x: x[0] if isinstance(x, (list, tuple)) else "")
    df['Variable 2'] = df['variables'].apply(lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else "")
    
    # Select and rename columns for display
    display_cols = {
        'Variable 1': 'Variable 1',
        'Variable 2': 'Variable 2',
        'coefficient': 'Correlation',
        'p_value': 'P-Value',
        'sample_size': 'N',
        'method': 'Method'
    }
    
    df_display = df[list(display_cols.keys())].copy()
    df_display.columns = list(display_cols.values())
    
    # Format numeric columns
    df_display['Correlation'] = df_display['Correlation'].apply(lambda x: f"{x:.3f}")
    if 'P-Value' in df_display.columns:
        df_display['P-Value'] = df_display['P-Value'].apply(
            lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
        )
    
    # Sort controls
    col1, col2 = st.columns([2, 1])
    
    with col1:
        sort_by = st.selectbox(
            "Sort by",
            options=['Correlation (Abs)', 'Correlation', 'P-Value', 'N'],
            key="corr_sort"
        )
    
    with col2:
        ascending = st.checkbox("Ascending", value=False, key="corr_ascending")
    
    # Apply sorting
    if sort_by == 'Correlation (Abs)':
        df['abs_corr'] = df['coefficient'].abs()
        df_sorted = df.sort_values('abs_corr', ascending=ascending)
        df_display = df_sorted[list(display_cols.keys())].copy()
        df_display.columns = list(display_cols.values())
        df_display['Correlation'] = df_sorted['coefficient'].apply(lambda x: f"{x:.3f}")
    else:
        sort_col = {'Correlation': 'coefficient', 'P-Value': 'p_value', 'N': 'sample_size'}[sort_by]
        df_sorted = df.sort_values(sort_col, ascending=ascending)
        df_display = df_sorted[list(display_cols.keys())].copy()
        df_display.columns = list(display_cols.values())
    
    # Format again after sorting
    if 'P-Value' in df_display.columns:
        df_display['P-Value'] = df_sorted['p_value'].apply(
            lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
        )
    
    # Display table
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Summary statistics
    with st.expander("📊 Summary Statistics"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Pairs", len(df))
        
        with col2:
            avg_abs_corr = df['coefficient'].abs().mean()
            st.metric("Mean |Correlation|", f"{avg_abs_corr:.3f}")
        
        with col3:
            if 'p_value' in df.columns:
                significant = (df['p_value'] < 0.05).sum()
                st.metric("Significant (p<0.05)", significant)


def render_correlation_heatmap(records: List[Dict[str, Any]]) -> None:
    """Render interactive correlation heatmap.
    
    Args:
        records: List of correlation record dictionaries
    """
    st.subheader("Correlation Heatmap")
    
    # Build correlation matrix
    variables = set()
    for record in records:
        vars = record.get('variables', [])
        if isinstance(vars, (list, tuple)) and len(vars) == 2:
            variables.add(vars[0])
            variables.add(vars[1])
    
    variables = sorted(list(variables))
    n = len(variables)
    
    if n == 0:
        st.warning("No variables found for heatmap")
        return
    
    # Initialize matrix
    corr_matrix = np.eye(n)
    var_index = {var: idx for idx, var in enumerate(variables)}
    
    # Fill matrix
    for record in records:
        vars = record.get('variables', [])
        if isinstance(vars, (list, tuple)) and len(vars) == 2:
            i, j = var_index[vars[0]], var_index[vars[1]]
            coef = record.get('coefficient', 0)
            corr_matrix[i, j] = coef
            corr_matrix[j, i] = coef
    
    # Color scale selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        color_scale = st.selectbox(
            "Color Scale",
            options=['RdBu_r', 'Viridis', 'Cividis', 'RdYlGn'],
            key="heatmap_color"
        )
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=variables,
        y=variables,
        colorscale=color_scale,
        zmid=0,
        zmin=-1,
        zmax=1,
        text=np.round(corr_matrix, 3),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation"),
        hoverongaps=False
    ))
    
    fig.update_layout(
        title="Correlation Matrix",
        xaxis_title="",
        yaxis_title="",
        height=max(400, n * 30),
        width=max(400, n * 30)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Download option
    if st.button("📥 Download Heatmap Data (CSV)", key="download_heatmap"):
        df = pd.DataFrame(corr_matrix, index=variables, columns=variables)
        csv = df.to_csv()
        st.download_button(
            "Download CSV",
            data=csv,
            file_name="correlation_matrix.csv",
            mime="text/csv"
        )


def render_correlation_network(records: List[Dict[str, Any]]) -> None:
    """Render force-directed network graph of correlations.
    
    Args:
        records: List of correlation record dictionaries
    """
    st.subheader("Correlation Network")
    
    # Filter controls
    col1, col2 = st.columns(2)
    
    with col1:
        threshold = st.slider(
            "Minimum |Correlation|",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
            key="network_threshold"
        )
    
    with col2:
        max_edges = st.number_input(
            "Max Edges",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            key="network_max_edges"
        )
    
    # Filter records by threshold
    filtered = [
        r for r in records
        if abs(r.get('coefficient', 0)) >= threshold
    ]
    
    # Sort by absolute correlation and limit
    filtered = sorted(
        filtered,
        key=lambda x: abs(x.get('coefficient', 0)),
        reverse=True
    )[:max_edges]
    
    if not filtered:
        st.info(f"No correlations above threshold {threshold}")
        return
    
    # Build node and edge lists
    nodes = set()
    edges = []
    
    for record in filtered:
        vars = record.get('variables', [])
        if isinstance(vars, (list, tuple)) and len(vars) == 2:
            nodes.add(vars[0])
            nodes.add(vars[1])
            edges.append({
                'source': vars[0],
                'target': vars[1],
                'weight': abs(record.get('coefficient', 0)),
                'coefficient': record.get('coefficient', 0)
            })
    
    nodes = list(nodes)
    node_indices = {node: idx for idx, node in enumerate(nodes)}
    
    # Simple circular layout
    n = len(nodes)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x_pos = np.cos(angles)
    y_pos = np.sin(angles)
    
    # Create edge traces
    edge_traces = []
    for edge in edges:
        i = node_indices[edge['source']]
        j = node_indices[edge['target']]
        
        # Color based on correlation sign
        color = 'blue' if edge['coefficient'] > 0 else 'red'
        width = edge['weight'] * 3  # Scale line width by correlation strength
        
        edge_trace = go.Scatter(
            x=[x_pos[i], x_pos[j], None],
            y=[y_pos[i], y_pos[j], None],
            mode='lines',
            line=dict(color=color, width=width),
            hoverinfo='none',
            showlegend=False
        )
        edge_traces.append(edge_trace)
    
    # Create node trace
    node_trace = go.Scatter(
        x=x_pos,
        y=y_pos,
        mode='markers+text',
        text=nodes,
        textposition='top center',
        marker=dict(
            size=20,
            color='lightblue',
            line=dict(color='darkblue', width=2)
        ),
        hoverinfo='text',
        hovertext=nodes
    )
    
    # Create figure
    fig = go.Figure(data=edge_traces + [node_trace])
    
    fig.update_layout(
        title=f"Correlation Network ({len(filtered)} edges)",
        showlegend=False,
        hovermode='closest',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Legend
    st.caption("🔵 Positive correlation | 🔴 Negative correlation | Line thickness = strength")
