"""Reusable UI components for the RelatAI Streamlit application."""

# Configuration components
from .column_selector import render_column_selector
from .filter_panel import render_filter_panel
from .mode_selector import render_mode_selector
from .preview_table import render_preview_table, render_refresh_button

# Confidence flag components
from .confidence_flags import (
    render_confidence_badge,
    render_flag_summary,
    filter_by_severity,
    render_flag_filter,
    render_flags_inline,
    extract_flags_from_result
)

# Visualization components
from .correlation_view import render_correlation_results
from .multivariate_view import render_multivariate_results
from .autotriage_view import render_autotriage_results
from .ai_summary import render_ai_summary

# Phase 4 components - Polish & Advanced Features
from .audit_viewer import (
    render_audit_timeline,
    render_audit_entry,
    filter_audit_entries,
    render_audit_filters,
    render_audit_summary,
    get_action_icon,
    get_relative_time
)
from .help_system import (
    render_help_icon,
    render_method_help,
    render_interpretation_guide,
    render_best_practices,
    render_quick_help
)

__all__ = [
    # Configuration
    'render_column_selector',
    'render_filter_panel',
    'render_mode_selector',
    'render_preview_table',
    'render_refresh_button',
    
    # Confidence flags
    'render_confidence_badge',
    'render_flag_summary',
    'filter_by_severity',
    'render_flag_filter',
    'render_flags_inline',
    'extract_flags_from_result',
    
    # Visualizations
    'render_correlation_results',
    'render_multivariate_results',
    'render_autotriage_results',
    'render_ai_summary',
    
    # Audit Trail
    'render_audit_timeline',
    'render_audit_entry',
    'filter_audit_entries',
    'render_audit_filters',
    'render_audit_summary',
    'get_action_icon',
    'get_relative_time',
    
    # Help System
    'render_help_icon',
    'render_method_help',
    'render_interpretation_guide',
    'render_best_practices',
    'render_quick_help',
]
