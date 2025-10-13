# Preprocessing Developer Guide

**Version**: 1.0  
**Last Updated**: October 13, 2025  
**Audience**: Developers, Contributors

---

## Overview

This guide explains how to extend the preprocessing pipeline with new strategies, add custom transformations, and integrate with the audit trail system.

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Dataset Upload Flow                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ingestion.py: ingest_dataset_upload()                      │
│  • Saves file to disk                                        │
│  • Computes dataset hash                                     │
│  • Initializes audit log                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  preprocessing.py: preprocess_frame()                       │
│  • Creates deep copy of DataFrame                            │
│  • Applies transformation strategies                         │
│  • Records audit actions                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  audit_trail.py: record_preprocessing_action()              │
│  • Stores action details                                     │
│  • Timestamps transformation                                 │
│  • Thread-safe operation                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  schema_detection.py: profile_frame()                       │
│  • Generates column statistics                               │
│  • Returns processed DataFrame                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Immutability**: Original frame is copied; preprocessing operates on the copy
2. **Audit-First**: Every transformation is logged before returning
3. **Configuration-Driven**: Strategies controlled via `PreprocessingConfig`
4. **Fail-Safe**: Invalid configurations raise `ValueError` at initialization
5. **Modularity**: Each strategy is isolated in its own function

---

## Adding a New Preprocessing Strategy

### Example: Adding KNN Imputation

#### Step 1: Update Type Definitions

```python
# File: backend/relat_ai/services/preprocessing.py

# Add new strategy to Literal type
MissingNumericStrategy = Literal["median", "mean", "zero", "knn"]  # Added "knn"
```

#### Step 2: Update PreprocessingConfig

```python
@dataclass(slots=True)
class PreprocessingConfig:
    """Configuration options controlling preprocessing behaviour."""

    missing_numeric: MissingNumericStrategy = "median"
    missing_categorical: MissingCategoricalStrategy = "mode"
    missing_constant_value: str = "Unknown"
    outlier_strategy: OutlierStrategy = "iqr_clip"
    scaling_strategy: ScalingStrategy = "robust"
    knn_neighbors: int = 5  # ✅ Add strategy-specific parameter

    def __post_init__(self) -> None:
        # ✅ Update validation
        if self.missing_numeric not in {"median", "mean", "zero", "knn"}:
            raise ValueError(f"Unsupported numeric imputation strategy: {self.missing_numeric}")
        # ... existing validation ...
        
        # ✅ Add parameter validation
        if self.knn_neighbors < 1:
            raise ValueError("knn_neighbors must be at least 1")
```

#### Step 3: Implement Strategy Function

```python
def _handle_missing_numeric(
    frame: pd.DataFrame, dataset_id: str, config: PreprocessingConfig
) -> None:
    """Handle missing values in numeric columns."""
    
    numeric_columns = frame.select_dtypes(include=[np.number]).columns
    for column in numeric_columns:
        series = frame[column]
        missing_mask = series.isna()
        missing_count = int(missing_mask.sum())
        if missing_count == 0:
            continue

        # ✅ Add new strategy branch
        if config.missing_numeric == "knn":
            from sklearn.impute import KNNImputer
            
            # Prepare data for KNN imputation
            imputer = KNNImputer(n_neighbors=config.knn_neighbors)
            numeric_data = frame[numeric_columns].values
            imputed_data = imputer.fit_transform(numeric_data)
            
            # Extract the filled column
            col_idx = list(numeric_columns).index(column)
            fill_values = imputed_data[missing_mask, col_idx]
            frame.loc[missing_mask, column] = fill_values
            
            # Record audit action with KNN-specific details
            record_preprocessing_action(
                dataset_id,
                action_type="missing_imputation",
                column=column,
                details={
                    "strategy": "knn",
                    "n_neighbors": config.knn_neighbors,
                    "imputed_count": missing_count,
                },
            )
            continue  # Skip default logic
        
        # Existing median/mean/zero logic...
        if config.missing_numeric == "median":
            fill_value = float(series.median(skipna=True)) if not series.dropna().empty else 0.0
        elif config.missing_numeric == "mean":
            fill_value = float(series.mean(skipna=True)) if not series.dropna().empty else 0.0
        else:  # "zero"
            fill_value = 0.0

        frame[column] = series.fillna(fill_value)
        record_preprocessing_action(
            dataset_id,
            action_type="missing_imputation",
            column=column,
            details={
                "strategy": config.missing_numeric,
                "fill_value": fill_value,
                "imputed_count": missing_count,
            },
        )
```

#### Step 4: Update Configuration from Settings

```python
@classmethod
def from_settings(cls, settings: object) -> "PreprocessingConfig":
    """Create a configuration from a settings object."""

    attrs = {
        "missing_numeric": getattr(settings, "preprocessing_missing_numeric", "median"),
        "missing_categorical": getattr(settings, "preprocessing_missing_categorical", "mode"),
        "missing_constant_value": getattr(settings, "preprocessing_missing_constant", "Unknown"),
        "outlier_strategy": getattr(settings, "preprocessing_outlier_strategy", "iqr_clip"),
        "scaling_strategy": getattr(settings, "preprocessing_scaling_strategy", "robust"),
        "knn_neighbors": getattr(settings, "preprocessing_knn_neighbors", 5),  # ✅ Add new setting
    }
    return cls(**attrs)
```

#### Step 5: Add Configuration to Settings

```python
# File: backend/relat_ai/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    preprocessing_knn_neighbors: int = Field(
        default=5, alias="PREPROCESSING_KNN_NEIGHBORS"
    )  # ✅ Add new setting
```

#### Step 6: Update .env.example

```bash
# File: backend/.env.example

# KNN imputation parameters (when PREPROCESSING_MISSING_NUMERIC=knn)
PREPROCESSING_KNN_NEIGHBORS=5
```

#### Step 7: Add Tests

```python
# File: backend/relat_ai/tests/unit/test_preprocessing.py

def test_preprocessing_strategies_knn_imputation() -> None:
    """Test KNN imputation strategy for numeric columns."""

    frame = pd.DataFrame({
        "x": [1.0, 2.0, np.nan, 4.0, 5.0],
        "y": [2.0, 4.0, 6.0, 8.0, 10.0],
    })
    dataset_id = "dataset-knn"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="knn.csv",
        dataset_hash="hash_knn",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig(
        missing_numeric="knn", 
        knn_neighbors=2,
        outlier_strategy="none",
        scaling_strategy="none"
    )
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # Missing value should be imputed based on neighbors
    assert processed["x"].isna().sum() == 0
    # Expect value close to 3.0 based on neighbors [2.0, 4.0]
    assert abs(processed["x"].iloc[2] - 3.0) < 0.5

    # Verify audit log
    log = get_audit_log(dataset_id)
    assert log is not None
    x_actions = [a for a in log.actions if a.column == "x"]
    assert len(x_actions) == 1
    assert x_actions[0].details["strategy"] == "knn"
    assert x_actions[0].details["n_neighbors"] == 2
```

#### Step 8: Update Documentation

```markdown
# File: docs/AuditTrail_UserGuide.md

### Missing Value Strategies

- **median**: Fill with column median (default for numeric)
- **mean**: Fill with column mean
- **zero**: Fill with 0.0
- **knn**: Use K-Nearest Neighbors imputation (requires sklearn)
- **mode**: Fill with most common value (default for categorical)
- **constant**: Fill with specified constant value
```

---

## Adding a New Transformation Type

### Example: Adding Feature Engineering (Log Transform)

#### Step 1: Define New Action Type

```python
# No code changes needed - action_type is a free-form string
# But document conventions for consistency
```

#### Step 2: Create Transformation Function

```python
def _apply_feature_engineering(
    frame: pd.DataFrame, dataset_id: str, config: PreprocessingConfig
) -> None:
    """Apply feature engineering transformations."""
    
    if not config.enable_feature_engineering:
        return
    
    numeric_columns = frame.select_dtypes(include=[np.number]).columns
    for column in numeric_columns:
        series = frame[column]
        
        # Skip if column has non-positive values
        if (series <= 0).any():
            continue
        
        # Create log-transformed feature
        log_column_name = f"{column}_log"
        frame[log_column_name] = np.log(series)
        
        record_preprocessing_action(
            dataset_id,
            action_type="feature_engineering",  # ✅ New action type
            column=log_column_name,
            details={
                "transformation": "log",
                "source_column": column,
            },
        )
```

#### Step 3: Integrate into Pipeline

```python
def preprocess_frame(
    frame: pd.DataFrame,
    *,
    dataset_id: str,
    config: PreprocessingConfig,
) -> pd.DataFrame:
    """Apply preprocessing steps to a dataframe while logging actions."""

    processed = frame.copy(deep=True)

    _handle_missing_numeric(processed, dataset_id, config)
    _handle_missing_categorical(processed, dataset_id, config)
    _handle_outliers(processed, dataset_id, config)
    _apply_scaling(processed, dataset_id, config)
    _apply_feature_engineering(processed, dataset_id, config)  # ✅ Add new step

    return processed
```

---

## Best Practices

### ✅ Do

1. **Always log actions** - Every transformation must call `record_preprocessing_action()`
2. **Validate configuration** - Add `__post_init__` checks for new parameters
3. **Handle edge cases** - Check for empty series, zero variance, all-missing
4. **Use type hints** - Maintain type safety with `Literal` types
5. **Test thoroughly** - Add unit tests for normal and edge cases
6. **Document strategies** - Update user guide with new options
7. **Fail early** - Raise `ValueError` for invalid configurations at init time
8. **Copy before modify** - Never modify the original DataFrame
9. **Check before act** - Skip processing if no work is needed (e.g., no missing values)
10. **Thread safety** - Use audit trail functions (already thread-safe)

### ❌ Don't

1. **Modify in-place without copy** - Always operate on a copy
2. **Skip audit logging** - Every transformation must be logged
3. **Use mutable defaults** - Use `field(default_factory=...)` for lists/dicts
4. **Ignore edge cases** - Handle empty, all-missing, zero-variance data
5. **Assume data types** - Use `select_dtypes()` to filter columns
6. **Hardcode values** - Make behavior configurable
7. **Raise in processing** - Prefer logging warnings and continuing
8. **Break existing configs** - Maintain backward compatibility
9. **Skip tests** - Test both success and failure paths
10. **Forget documentation** - Update both user and developer guides

---

## Testing Guidelines

### Unit Test Structure

```python
def test_new_strategy_name() -> None:
    """Clear description of what is being tested."""
    
    # 1. Setup: Create test DataFrame
    frame = pd.DataFrame({...})
    dataset_id = "test-id"
    
    # 2. Initialize audit log
    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="test.csv",
        dataset_hash="hash",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )
    
    # 3. Create configuration
    config = PreprocessingConfig(
        missing_numeric="new_strategy",
        # ... other settings
    )
    
    # 4. Execute preprocessing
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)
    
    # 5. Assert results
    assert processed["column"].isna().sum() == 0
    assert some_condition_is_true
    
    # 6. Verify audit log
    log = get_audit_log(dataset_id)
    assert log is not None
    actions = [a for a in log.actions if a.column == "column"]
    assert len(actions) == 1
    assert actions[0].action_type == "expected_type"
    assert actions[0].details["key"] == "expected_value"
```

### Test Categories to Cover

1. **Happy Path**: Strategy works as expected
2. **Edge Cases**: Empty data, all-missing, single value
3. **Configuration Validation**: Invalid parameters raise errors
4. **Audit Logging**: Actions are recorded correctly
5. **No-Op Cases**: Skip processing when not needed
6. **Integration**: Works with other strategies in pipeline

---

## Common Patterns

### Pattern 1: Column-Wise Processing

```python
def _transform_columns(frame: pd.DataFrame, dataset_id: str, config: Config) -> None:
    columns = frame.select_dtypes(include=[np.number]).columns
    for column in columns:
        series = frame[column]
        
        # Check if processing needed
        if not needs_processing(series):
            continue
        
        # Apply transformation
        transformed = transform(series, config)
        frame[column] = transformed
        
        # Log action
        record_preprocessing_action(
            dataset_id,
            action_type="transformation_type",
            column=column,
            details={"param": value},
        )
```

### Pattern 2: Conditional Processing

```python
def _conditional_transform(frame: pd.DataFrame, dataset_id: str, config: Config) -> None:
    if config.strategy == "none":
        return  # Skip processing
    
    if config.strategy == "option_a":
        result = method_a(frame)
    elif config.strategy == "option_b":
        result = method_b(frame)
    else:
        raise ValueError(f"Unknown strategy: {config.strategy}")
    
    # Apply result and log
    frame[...] = result
    record_preprocessing_action(...)
```

### Pattern 3: Fallback Values

```python
def _compute_fill_value(series: pd.Series, strategy: str) -> float:
    """Compute fill value with safe fallbacks."""
    
    clean = series.dropna()
    if clean.empty:
        return 0.0  # Fallback for all-missing
    
    if strategy == "median":
        return float(clean.median())
    elif strategy == "mean":
        return float(clean.mean())
    else:
        return 0.0
```

---

## Debugging Tips

### Enable Detailed Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Audit Trail

```python
from relat_ai.services.audit_trail import get_audit_log

log = get_audit_log("your-dataset-id")
for action in log.actions:
    print(f"{action.timestamp}: {action.action_type} on {action.column}")
    print(f"  Details: {action.details}")
```

### Test Configuration Validation

```python
import pytest
from relat_ai.services.preprocessing import PreprocessingConfig

# Should raise
with pytest.raises(ValueError):
    PreprocessingConfig(missing_numeric="invalid")
```

### Verify DataFrame Changes

```python
original = frame.copy()
processed = preprocess_frame(frame, dataset_id="test", config=config)

# Check what changed
changed_columns = []
for col in original.columns:
    if not original[col].equals(processed[col]):
        changed_columns.append(col)
print(f"Changed columns: {changed_columns}")
```

---

## FAQ

**Q: How do I add a new configuration parameter?**  
A: Add field to `PreprocessingConfig`, update `from_settings()`, add to `Settings`, update `.env.example`

**Q: When should I log an action?**  
A: After every transformation that modifies data. Before returning the DataFrame.

**Q: How do I handle errors during preprocessing?**  
A: Prefer logging warnings and continuing. Only raise for configuration errors.

**Q: Can I add async preprocessing?**  
A: Not currently supported. Preprocessing is synchronous for simplicity and audit trail integrity.

**Q: How do I test thread safety?**  
A: Use `concurrent.futures` to run preprocessing on multiple datasets simultaneously.

**Q: Should I add dependencies for new strategies?**  
A: Prefer optional dependencies. Check if module is available before using.

---

## Resources

- **Code**: `backend/relat_ai/services/preprocessing.py`
- **Tests**: `backend/relat_ai/tests/unit/test_preprocessing.py`
- **Audit Trail**: `backend/relat_ai/services/audit_trail.py`
- **Configuration**: `backend/relat_ai/core/config.py`
- **User Guide**: `docs/AuditTrail_UserGuide.md`

---

**Document Version**: 1.0  
**Last Updated**: October 13, 2025  
**Contributors**: RelatAI Development Team
