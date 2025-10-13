# Audit Trail User Guide

**Version**: 1.0  
**Last Updated**: October 13, 2025  
**Audience**: Quality Engineers, Data Analysts, Compliance Officers

---

## Overview

The RelatAI audit trail system provides complete transparency into all data transformations applied during dataset ingestion. Every preprocessing action is logged with timestamps, details, and dataset identifiers to support:

- **Compliance & Traceability**: Meet regulatory requirements for data lineage
- **Reproducibility**: Understand exactly how data was transformed
- **Quality Assurance**: Verify preprocessing decisions during investigations
- **Debugging**: Identify unexpected data transformations

---

## Accessing Audit Logs

### Via REST API

**List All Audit Logs**:
```http
GET /audit/
```

**Response**:
```json
[
  {
    "dataset_id": "abc123",
    "dataset_name": "quality_data.csv",
    "dataset_hash": "sha256:a1b2c3...",
    "row_count": 5000,
    "column_count": 15,
    "created_at": "2025-10-13T14:30:00Z",
    "actions": [...]
  }
]
```

**Retrieve Specific Dataset Audit Log**:
```http
GET /audit/{dataset_id}
```

**Response**:
```json
{
  "dataset_id": "abc123",
  "dataset_name": "quality_data.csv",
  "dataset_hash": "sha256:a1b2c3...",
  "row_count": 5000,
  "column_count": 15,
  "created_at": "2025-10-13T14:30:00Z",
  "actions": [
    {
      "action_type": "dataset_ingested",
      "timestamp": "2025-10-13T14:30:00Z",
      "column": null,
      "details": {
        "row_count": 5000,
        "column_count": 15,
        "file_size_bytes": 245000,
        "content_type": "text/csv"
      }
    },
    {
      "action_type": "missing_imputation",
      "timestamp": "2025-10-13T14:30:01Z",
      "column": "temperature",
      "details": {
        "strategy": "median",
        "fill_value": 22.5,
        "imputed_count": 45
      }
    },
    {
      "action_type": "outlier_clipping",
      "timestamp": "2025-10-13T14:30:02Z",
      "column": "pressure",
      "details": {
        "strategy": "iqr_clip",
        "lower_bound": 50.0,
        "upper_bound": 150.0,
        "clipped_count": 12
      }
    },
    {
      "action_type": "scaling",
      "timestamp": "2025-10-13T14:30:03Z",
      "column": "flow_rate",
      "details": {
        "strategy": "robust",
        "median": 100.5,
        "iqr": 25.3
      }
    }
  ]
}
```

---

## Understanding Audit Log Fields

### Dataset-Level Fields

| Field | Description | Example |
|-------|-------------|---------|
| `dataset_id` | Unique identifier for the dataset | `"abc123"` |
| `dataset_name` | Original filename uploaded | `"quality_data.csv"` |
| `dataset_hash` | SHA-256 hash of the raw file for integrity verification | `"sha256:a1b2c3..."` |
| `row_count` | Number of rows after preprocessing | `5000` |
| `column_count` | Number of columns after preprocessing | `15` |
| `created_at` | Timestamp when audit log was initialized (UTC) | `"2025-10-13T14:30:00Z"` |

### Action-Level Fields

| Field | Description | Example |
|-------|-------------|---------|
| `action_type` | Type of preprocessing action (see below) | `"missing_imputation"` |
| `timestamp` | When the action was performed (UTC) | `"2025-10-13T14:30:01Z"` |
| `column` | Column affected (null for dataset-level actions) | `"temperature"` |
| `details` | Action-specific details (varies by action type) | `{"strategy": "median", ...}` |

---

## Action Types Reference

### 1. `dataset_ingested`

**When**: Dataset is successfully uploaded  
**Column**: `null` (dataset-level action)  
**Details**:
```json
{
  "row_count": 5000,
  "column_count": 15,
  "file_size_bytes": 245000,
  "content_type": "text/csv"
}
```

**Interpretation**: Confirms the dataset was ingested with the specified dimensions.

---

### 2. `missing_imputation`

**When**: Missing values are filled in a column  
**Column**: Name of the column with missing values  
**Details**:
```json
{
  "strategy": "median",        // "median", "mean", "zero", "mode", or "constant"
  "fill_value": 22.5,          // Value used to fill missing entries
  "imputed_count": 45          // Number of missing values filled
}
```

**Interpretation**: 
- **Numeric columns**: Missing values filled with median, mean, or zero
- **Categorical columns**: Missing values filled with mode or constant value
- If `imputed_count` is high relative to total rows, consider data quality issues

**Example**:
> "Column 'temperature' had 45 missing values (0.9% of data) filled with median value 22.5°C"

---

### 3. `outlier_clipping`

**When**: Extreme values are clipped to acceptable bounds  
**Column**: Name of numeric column with outliers  
**Details**:
```json
{
  "strategy": "iqr_clip",      // Currently only "iqr_clip" is supported
  "lower_bound": 50.0,         // Values below this were clipped to this value
  "upper_bound": 150.0,        // Values above this were clipped to this value
  "clipped_count": 12          // Number of values clipped
}
```

**Interpretation**:
- Uses Interquartile Range (IQR) method: Q1 - 1.5×IQR and Q3 + 1.5×IQR
- Values outside bounds are clipped (not removed)
- If `clipped_count` is high, investigate data source for quality issues

**Example**:
> "Column 'pressure' had 12 outlier values (0.24% of data) clipped to range [50.0, 150.0] psi using IQR method"

---

### 4. `scaling`

**When**: Numeric column is scaled for analysis  
**Column**: Name of numeric column scaled  
**Details**:
```json
{
  "strategy": "robust",        // Currently only "robust" is supported
  "median": 100.5,             // Original median of the column
  "iqr": 25.3                  // Original IQR (Q3 - Q1) of the column
}
```

**Interpretation**:
- Robust scaling: `(value - median) / IQR`
- Makes data more comparable across different measurement scales
- Scaled values typically range from -3 to +3
- Original scale can be recovered: `original = (scaled × IQR) + median`

**Example**:
> "Column 'flow_rate' was scaled using robust scaler (median=100.5, IQR=25.3)"

---

## Common Use Cases

### Use Case 1: Verify Data Integrity

**Question**: "Has my data been modified?"

**Solution**:
1. Retrieve audit log for your dataset
2. Check `dataset_hash` to verify file integrity
3. Review all `actions` to see what transformations were applied
4. Compare `row_count` and `column_count` before/after

```bash
# Example: Check if any outliers were clipped
curl http://localhost:8000/audit/abc123 | jq '.actions[] | select(.action_type=="outlier_clipping")'
```

---

### Use Case 2: Reproduce Analysis Results

**Question**: "Why did I get different results from the same file?"

**Solution**:
1. Compare `dataset_hash` values to confirm same raw data
2. Check preprocessing strategies in environment configuration
3. Verify `timestamp` sequence matches expected order
4. Review `fill_value` and `clipped_count` for differences

---

### Use Case 3: Compliance Audit

**Question**: "Demonstrate data transformations for regulatory review"

**Solution**:
1. Export audit log as JSON for external auditors
2. Provide interpretation guide (this document)
3. Highlight:
   - `created_at` timestamp for workflow timing
   - `dataset_hash` for data integrity proof
   - All `actions` with details for full transparency

---

### Use Case 4: Quality Investigation

**Question**: "Why is my analysis showing unexpected correlations?"

**Solution**:
1. Check `missing_imputation` actions:
   - High `imputed_count` may introduce bias
   - Verify `strategy` and `fill_value` are appropriate
2. Check `outlier_clipping` actions:
   - Clipping may mask important signals
   - Review `clipped_count` relative to total observations
3. Check `scaling` actions:
   - Verify scaling hasn't distorted relationships

---

## Preprocessing Configuration

Preprocessing behavior is controlled via environment variables:

```bash
# Missing value strategies
PREPROCESSING_MISSING_NUMERIC=median        # median, mean, zero
PREPROCESSING_MISSING_CATEGORICAL=mode      # mode, constant
PREPROCESSING_MISSING_CONSTANT=Unknown      # Value when strategy=constant

# Outlier handling
PREPROCESSING_OUTLIER_STRATEGY=iqr_clip     # none, iqr_clip

# Scaling
PREPROCESSING_SCALING_STRATEGY=robust       # none, robust
```

**Default Configuration**:
- Numeric missing values: filled with **median**
- Categorical missing values: filled with **mode**
- Outliers: **clipped** using IQR method
- Scaling: **robust** scaling applied

---

## Best Practices

### ✅ Do

1. **Review audit logs after upload** - Verify preprocessing met expectations
2. **Check imputed_count** - High imputation rates may indicate data quality issues
3. **Document configuration** - Save environment variables used for reproducibility
4. **Archive audit logs** - Export logs for compliance and long-term records
5. **Compare hashes** - Verify data integrity using `dataset_hash`

### ❌ Don't

1. **Ignore high imputation counts** - Investigate data source quality
2. **Overlook clipped outliers** - May indicate sensor failures or data issues
3. **Assume default settings are always correct** - Configure for your use case
4. **Skip audit review** - Preprocessing can significantly impact analysis results

---

## Troubleshooting

### Problem: Audit log not found (404 error)

**Cause**: Dataset was uploaded before audit trail system was implemented, or dataset_id is incorrect

**Solution**: Re-upload the dataset or verify the correct `dataset_id`

---

### Problem: Unexpected imputation counts

**Cause**: Data source has quality issues or incorrect null encoding

**Solution**: 
1. Check raw data file for null values
2. Verify null encoding (blank, "NA", "NULL", etc.)
3. Consider cleaning data at source

---

### Problem: Too many outliers clipped

**Cause**: Data distribution is non-normal or IQR method too aggressive

**Solution**:
1. Review data distribution
2. Consider setting `PREPROCESSING_OUTLIER_STRATEGY=none`
3. Handle outliers manually after export

---

### Problem: Cannot reproduce results

**Cause**: Different preprocessing configuration or dataset version

**Solution**:
1. Compare `dataset_hash` values
2. Compare `created_at` timestamps
3. Compare all `actions` and `details`
4. Verify environment configuration matches

---

## FAQ

**Q: Are audit logs persisted across server restarts?**  
A: No, audit logs are currently stored in-memory. Future versions will add database persistence. Export logs for long-term storage.

**Q: Can I disable preprocessing?**  
A: Yes, set all strategies to "none":
```bash
PREPROCESSING_MISSING_NUMERIC=median  # Still need imputation strategy
PREPROCESSING_OUTLIER_STRATEGY=none
PREPROCESSING_SCALING_STRATEGY=none
```
Note: Missing value imputation is always performed to prevent analysis errors.

**Q: How do I export audit logs?**  
A: Use the REST API and save JSON response:
```bash
curl http://localhost:8000/audit/abc123 > audit_log.json
```

**Q: Can I modify audit logs?**  
A: No, audit logs are read-only to maintain integrity. They are automatically generated during upload.

**Q: What timezone are timestamps in?**  
A: All timestamps are in UTC (Coordinated Universal Time).

**Q: How long are audit logs retained?**  
A: Currently, audit logs are retained in-memory until server restart. Export important logs for permanent records.

---

## Support

For questions or issues with audit logs:
- Check this guide first
- Review the Technical Specification (docs/TechnicalSpecification.md)
- Consult the API documentation at `/docs` endpoint
- File an issue in the repository

---

**Document Version**: 1.0  
**Last Updated**: October 13, 2025  
**Next Review**: Quarterly or when preprocessing strategies change
