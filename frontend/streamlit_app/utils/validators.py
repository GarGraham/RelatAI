"""Input validation utilities for RelatAI frontend.

Provides validation functions for user inputs, configurations,
and data quality checks with detailed error messages.
"""

from typing import Any, List, Optional, Tuple, Dict
import pandas as pd
from pathlib import Path


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, is_valid: bool, message: str = "", details: Optional[Dict] = None):
        self.is_valid = is_valid
        self.message = message
        self.details = details or {}
    
    def __bool__(self):
        return self.is_valid


# File validation
def validate_file_upload(
    file: Any,
    allowed_extensions: List[str] = None,
    max_size_mb: float = 100.0
) -> ValidationResult:
    """Validate uploaded file.
    
    Args:
        file: Uploaded file object
        allowed_extensions: List of allowed file extensions
        max_size_mb: Maximum file size in MB
    
    Returns:
        ValidationResult
    """
    if file is None:
        return ValidationResult(False, "No file selected")
    
    # Check extension
    if allowed_extensions:
        file_ext = Path(file.name).suffix.lower()
        if file_ext not in allowed_extensions:
            return ValidationResult(
                False,
                f"Invalid file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}",
                {"extension": file_ext, "allowed": allowed_extensions}
            )
    
    # Check size
    if hasattr(file, 'size'):
        size_mb = file.size / (1024 * 1024)
        if size_mb > max_size_mb:
            return ValidationResult(
                False,
                f"File too large: {size_mb:.1f}MB. Maximum: {max_size_mb}MB",
                {"size_mb": size_mb, "max_size_mb": max_size_mb}
            )
    
    return ValidationResult(True, "File is valid")


def validate_dataset_columns(
    selected_columns: List[str],
    available_columns: List[str],
    min_columns: int = 2
) -> ValidationResult:
    """Validate column selection.
    
    Args:
        selected_columns: List of selected column names
        available_columns: List of available column names
        min_columns: Minimum number of columns required
    
    Returns:
        ValidationResult
    """
    if not selected_columns:
        return ValidationResult(False, "No columns selected")
    
    if len(selected_columns) < min_columns:
        return ValidationResult(
            False,
            f"At least {min_columns} columns required. Selected: {len(selected_columns)}",
            {"selected": len(selected_columns), "required": min_columns}
        )
    
    # Check all selected columns exist
    invalid_columns = [col for col in selected_columns if col not in available_columns]
    if invalid_columns:
        return ValidationResult(
            False,
            f"Invalid columns: {', '.join(invalid_columns)}",
            {"invalid": invalid_columns}
        )
    
    return ValidationResult(True, f"{len(selected_columns)} columns selected")


def validate_filters(
    filters: Dict[str, Any],
    column_types: Dict[str, str]
) -> ValidationResult:
    """Validate filter configuration.
    
    Args:
        filters: Dictionary of filters
        column_types: Dictionary mapping column names to types
    
    Returns:
        ValidationResult
    """
    if not filters:
        return ValidationResult(True, "No filters to validate")
    
    for column, filter_config in filters.items():
        # Check column exists
        if column not in column_types:
            return ValidationResult(
                False,
                f"Filter references unknown column: {column}",
                {"column": column}
            )
        
        # Validate filter structure
        if not isinstance(filter_config, dict):
            return ValidationResult(
                False,
                f"Invalid filter format for column: {column}",
                {"column": column, "type": type(filter_config).__name__}
            )
        
        # Check required fields
        if 'operator' not in filter_config:
            return ValidationResult(
                False,
                f"Filter missing operator for column: {column}",
                {"column": column}
            )
        
        if 'value' not in filter_config:
            return ValidationResult(
                False,
                f"Filter missing value for column: {column}",
                {"column": column}
            )
    
    return ValidationResult(True, f"{len(filters)} filters validated")


def validate_analysis_mode(
    mode: str,
    parameters: Dict[str, Any],
    selected_columns: List[str]
) -> ValidationResult:
    """Validate analysis mode and parameters.
    
    Args:
        mode: Analysis mode name
        parameters: Mode-specific parameters
        selected_columns: Selected column names
    
    Returns:
        ValidationResult
    """
    valid_modes = ["correlation", "multivariate", "auto-triage"]
    
    if mode not in valid_modes:
        return ValidationResult(
            False,
            f"Invalid analysis mode: {mode}. Valid modes: {', '.join(valid_modes)}",
            {"mode": mode, "valid_modes": valid_modes}
        )
    
    # Mode-specific validation
    if mode == "correlation":
        if len(selected_columns) < 2:
            return ValidationResult(
                False,
                "Correlation analysis requires at least 2 columns",
                {"columns": len(selected_columns)}
            )
    
    elif mode == "multivariate":
        if len(selected_columns) < 2:
            return ValidationResult(
                False,
                "Multivariate analysis requires at least 2 columns (1 response + 1 predictor)",
                {"columns": len(selected_columns)}
            )
        
        # Check for anchor columns
        anchor_columns = parameters.get('anchor_columns', [])
        if not anchor_columns:
            return ValidationResult(
                False,
                "Multivariate analysis requires at least one anchor (response) variable",
                {"anchors": len(anchor_columns)}
            )
        
        # Validate max_variables
        max_vars = parameters.get('max_variables', 10)
        if max_vars < 1 or max_vars > 20:
            return ValidationResult(
                False,
                f"max_variables must be between 1 and 20. Got: {max_vars}",
                {"max_variables": max_vars}
            )
    
    elif mode == "auto-triage":
        if len(selected_columns) < 3:
            return ValidationResult(
                False,
                "Auto-triage analysis works best with at least 3 columns",
                {"columns": len(selected_columns)}
            )
    
    return ValidationResult(True, f"{mode} mode configuration is valid")


def validate_numeric_range(
    value: float,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "value"
) -> ValidationResult:
    """Validate numeric value is within range.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        field_name: Name of field for error message
    
    Returns:
        ValidationResult
    """
    if not isinstance(value, (int, float)):
        return ValidationResult(
            False,
            f"{field_name} must be a number. Got: {type(value).__name__}",
            {"value": value, "type": type(value).__name__}
        )
    
    if min_value is not None and value < min_value:
        return ValidationResult(
            False,
            f"{field_name} must be at least {min_value}. Got: {value}",
            {"value": value, "min": min_value}
        )
    
    if max_value is not None and value > max_value:
        return ValidationResult(
            False,
            f"{field_name} must be at most {max_value}. Got: {value}",
            {"value": value, "max": max_value}
        )
    
    return ValidationResult(True, f"{field_name} is valid: {value}")


def validate_dataframe(
    df: pd.DataFrame,
    min_rows: int = 10,
    min_columns: int = 2,
    check_nulls: bool = True
) -> ValidationResult:
    """Validate DataFrame for analysis.
    
    Args:
        df: DataFrame to validate
        min_rows: Minimum number of rows required
        min_columns: Minimum number of columns required
        check_nulls: Whether to check for null values
    
    Returns:
        ValidationResult
    """
    if df is None:
        return ValidationResult(False, "DataFrame is None")
    
    if not isinstance(df, pd.DataFrame):
        return ValidationResult(
            False,
            f"Expected DataFrame, got {type(df).__name__}",
            {"type": type(df).__name__}
        )
    
    # Check dimensions
    if len(df) < min_rows:
        return ValidationResult(
            False,
            f"Dataset has too few rows: {len(df)}. Minimum: {min_rows}",
            {"rows": len(df), "min_rows": min_rows}
        )
    
    if len(df.columns) < min_columns:
        return ValidationResult(
            False,
            f"Dataset has too few columns: {len(df.columns)}. Minimum: {min_columns}",
            {"columns": len(df.columns), "min_columns": min_columns}
        )
    
    # Check for all-null columns
    if check_nulls:
        null_columns = df.columns[df.isnull().all()].tolist()
        if null_columns:
            return ValidationResult(
                False,
                f"Columns contain only null values: {', '.join(null_columns)}",
                {"null_columns": null_columns}
            )
    
    return ValidationResult(
        True,
        f"DataFrame is valid: {len(df)} rows × {len(df.columns)} columns"
    )


def validate_configuration(config: Dict[str, Any]) -> ValidationResult:
    """Validate complete analysis configuration.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        ValidationResult
    """
    required_keys = ['selected_columns', 'analysis_mode']
    
    # Check required keys
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        return ValidationResult(
            False,
            f"Configuration missing required keys: {', '.join(missing_keys)}",
            {"missing": missing_keys}
        )
    
    # Validate selected columns
    if not config['selected_columns']:
        return ValidationResult(False, "No columns selected in configuration")
    
    # Validate analysis mode
    valid_modes = ["correlation", "multivariate", "auto-triage"]
    if config['analysis_mode'] not in valid_modes:
        return ValidationResult(
            False,
            f"Invalid analysis mode: {config['analysis_mode']}",
            {"mode": config['analysis_mode'], "valid_modes": valid_modes}
        )
    
    return ValidationResult(True, "Configuration is valid")


def validate_template_name(name: str) -> ValidationResult:
    """Validate template name.
    
    Args:
        name: Template name
    
    Returns:
        ValidationResult
    """
    if not name or not name.strip():
        return ValidationResult(False, "Template name cannot be empty")
    
    if len(name) > 100:
        return ValidationResult(
            False,
            f"Template name too long: {len(name)} characters. Maximum: 100",
            {"length": len(name)}
        )
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    found_invalid = [char for char in invalid_chars if char in name]
    if found_invalid:
        return ValidationResult(
            False,
            f"Template name contains invalid characters: {', '.join(found_invalid)}",
            {"invalid_chars": found_invalid}
        )
    
    return ValidationResult(True, "Template name is valid")


def validate_export_options(
    format: str,
    available_formats: List[str] = None
) -> ValidationResult:
    """Validate export format selection.
    
    Args:
        format: Export format
        available_formats: List of available formats
    
    Returns:
        ValidationResult
    """
    if available_formats is None:
        available_formats = ["json", "csv", "excel", "png"]
    
    if format not in available_formats:
        return ValidationResult(
            False,
            f"Invalid export format: {format}. Available: {', '.join(available_formats)}",
            {"format": format, "available": available_formats}
        )
    
    return ValidationResult(True, f"Export format '{format}' is valid")
