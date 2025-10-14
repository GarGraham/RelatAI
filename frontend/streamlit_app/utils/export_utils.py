"""Export utility functions for RelatAI analysis results.

Provides functions to export analysis results, visualizations, and datasets
in various formats (JSON, CSV, Excel, PNG).
"""

import json
import io
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime


def export_results_json(results: Dict[str, Any], mode: str) -> str:
    """Export analysis results as formatted JSON string.
    
    Args:
        results: Analysis results dictionary
        mode: Analysis mode ('correlation', 'multivariate', 'auto-triage')
    
    Returns:
        Formatted JSON string
    """
    export_data = {
        "export_metadata": {
            "exported_at": datetime.now().isoformat(),
            "analysis_mode": mode,
            "version": "1.0"
        },
        "results": results
    }
    
    return json.dumps(export_data, indent=2)


def export_correlation_csv(results: Dict[str, Any]) -> str:
    """Export correlation results as CSV string.
    
    Args:
        results: Correlation analysis results
    
    Returns:
        CSV string with correlation table
    """
    table = results.get("correlation_table", {})
    records = table.get("records", [])
    
    if not records:
        return "No correlation data available"
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Format variables column
    df['Variable 1'] = df['variables'].apply(lambda x: x[0] if isinstance(x, (list, tuple)) else "")
    df['Variable 2'] = df['variables'].apply(lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else "")
    
    # Select columns for export
    export_df = df[['Variable 1', 'Variable 2', 'coefficient', 'p_value', 'sample_size', 'method']].copy()
    export_df.columns = ['Variable_1', 'Variable_2', 'Correlation', 'P_Value', 'Sample_Size', 'Method']
    
    # Convert to CSV
    return export_df.to_csv(index=False)


def export_multivariate_csv(results: Dict[str, Any]) -> str:
    """Export multivariate results as CSV string.
    
    Args:
        results: Multivariate analysis results
    
    Returns:
        CSV string with coefficient table
    """
    summary = results.get("model_summary", {})
    coefficients = summary.get('coefficients', [])
    
    if not coefficients:
        return "No coefficient data available"
    
    # Convert to DataFrame
    df = pd.DataFrame(coefficients)
    
    # Select columns for export
    export_cols = ['variable', 'coefficient', 'std_error', 't_statistic', 'p_value']
    export_df = df[[col for col in export_cols if col in df.columns]].copy()
    
    # Rename for clarity
    column_mapping = {
        'variable': 'Variable',
        'coefficient': 'Coefficient',
        'std_error': 'Std_Error',
        't_statistic': 'T_Statistic',
        'p_value': 'P_Value'
    }
    export_df.columns = [column_mapping.get(col, col) for col in export_df.columns]
    
    # Add model summary as header rows
    header_data = [
        ['Model Summary', ''],
        ['Target Variable', summary.get('target_variable', 'Unknown')],
        ['R_Squared', summary.get('r_squared', 0)],
        ['Adj_R_Squared', summary.get('adj_r_squared', 0)],
        ['N_Observations', summary.get('n_observations', 0)],
        ['', ''],
        ['Coefficients', '']
    ]
    
    header_df = pd.DataFrame(header_data)
    
    # Combine header and data
    csv_buffer = io.StringIO()
    header_df.to_csv(csv_buffer, index=False, header=False)
    export_df.to_csv(csv_buffer, index=False)
    
    return csv_buffer.getvalue()


def export_autotriage_csv(results: Dict[str, Any]) -> str:
    """Export auto-triage results as CSV string.
    
    Args:
        results: Auto-triage analysis results
    
    Returns:
        CSV string with suspicion rankings
    """
    rankings = results.get('suspicion_rankings', [])
    
    if not rankings:
        return "No suspicion ranking data available"
    
    # Convert to DataFrame
    df = pd.DataFrame(rankings)
    
    # Select columns for export
    export_cols = [
        'column_name', 'total_score', 'missing_score', 'outlier_score',
        'distribution_score', 'correlation_score', 'pattern_score',
        'missing_pct', 'outlier_count', 'flag_count'
    ]
    export_df = df[[col for col in export_cols if col in df.columns]].copy()
    
    # Rename for clarity
    export_df.columns = [col.replace('_', ' ').title().replace(' ', '_') for col in export_df.columns]
    
    # Sort by total score
    export_df = export_df.sort_values('Total_Score', ascending=False)
    
    return export_df.to_csv(index=False)


def export_visualization_data(
    results: Dict[str, Any],
    mode: str,
    viz_type: str
) -> Optional[str]:
    """Export visualization data in structured format.
    
    Args:
        results: Analysis results
        mode: Analysis mode
        viz_type: Visualization type (e.g., 'heatmap', 'network', 'biplot')
    
    Returns:
        CSV string with visualization data or None if not available
    """
    if mode == "correlation":
        if viz_type == "heatmap":
            return export_correlation_csv(results)
        elif viz_type == "network":
            # Export edge list for network
            table = results.get("correlation_table", {})
            records = table.get("records", [])
            
            edges = []
            for record in records:
                vars = record.get('variables', [])
                if isinstance(vars, (list, tuple)) and len(vars) == 2:
                    edges.append({
                        'Source': vars[0],
                        'Target': vars[1],
                        'Weight': record.get('coefficient', 0),
                        'P_Value': record.get('p_value', 1)
                    })
            
            if edges:
                df = pd.DataFrame(edges)
                return df.to_csv(index=False)
    
    elif mode == "multivariate":
        if viz_type == "coefficients":
            return export_multivariate_csv(results)
    
    elif mode == "auto-triage":
        if viz_type == "rankings":
            return export_autotriage_csv(results)
        elif viz_type == "pca":
            # Export PCA scores and loadings
            pca_data = results.get('pca_results', {})
            scores = pca_data.get('scores', [])
            
            if scores:
                df = pd.DataFrame(scores)
                df.columns = [f'PC{i+1}' for i in range(len(df.columns))]
                return df.to_csv(index=False)
    
    return None


def create_export_package(
    results: Dict[str, Any],
    mode: str,
    dataset_name: str = "dataset"
) -> Dict[str, str]:
    """Create a complete export package with multiple file formats.
    
    Args:
        results: Analysis results
        mode: Analysis mode
        dataset_name: Name of the dataset for file naming
    
    Returns:
        Dictionary mapping filenames to content strings
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{dataset_name}_{mode}_{timestamp}"
    
    package = {}
    
    # Always include full JSON results
    package[f"{base_name}_full_results.json"] = export_results_json(results, mode)
    
    # Mode-specific CSV exports
    if mode == "correlation":
        csv_data = export_correlation_csv(results)
        if csv_data:
            package[f"{base_name}_correlations.csv"] = csv_data
    
    elif mode == "multivariate":
        csv_data = export_multivariate_csv(results)
        if csv_data:
            package[f"{base_name}_coefficients.csv"] = csv_data
    
    elif mode == "auto-triage":
        csv_data = export_autotriage_csv(results)
        if csv_data:
            package[f"{base_name}_suspicion_rankings.csv"] = csv_data
    
    return package


def format_export_metadata(
    dataset_id: str,
    dataset_name: str,
    mode: str,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """Generate export metadata text file.
    
    Args:
        dataset_id: Dataset identifier
        dataset_name: Dataset name
        mode: Analysis mode
        config: Configuration used for analysis
    
    Returns:
        Formatted metadata string
    """
    metadata = [
        "RelatAI Analysis Export",
        "=" * 50,
        "",
        f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Dataset ID: {dataset_id}",
        f"Dataset Name: {dataset_name}",
        f"Analysis Mode: {mode}",
        "",
        "Configuration:",
        "-" * 50
    ]
    
    if config:
        for key, value in config.items():
            metadata.append(f"{key}: {value}")
    else:
        metadata.append("No configuration details available")
    
    metadata.extend([
        "",
        "=" * 50,
        "Generated by RelatAI Frontend",
        "Version: 1.0"
    ])
    
    return "\n".join(metadata)


def export_audit_log_csv(audit_entries: List[Dict[str, Any]]) -> str:
    """Export audit log entries as CSV.
    
    Args:
        audit_entries: List of audit log entry dictionaries
    
    Returns:
        CSV string with audit log data
    """
    if not audit_entries:
        return "No audit log entries available"
    
    # Convert to DataFrame
    df = pd.DataFrame(audit_entries)
    
    # Select relevant columns
    export_cols = [
        'timestamp', 'dataset_id', 'action', 'details', 
        'user', 'parameters', 'impact'
    ]
    
    # Only include columns that exist
    available_cols = [col for col in export_cols if col in df.columns]
    export_df = df[available_cols].copy()
    
    # Sort by timestamp (most recent first)
    if 'timestamp' in export_df.columns:
        export_df = export_df.sort_values('timestamp', ascending=False)
    
    return export_df.to_csv(index=False)
