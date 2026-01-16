# Bug Report: Correlation/Multivariate Crash with Object Columns

**Date**: 2025-10-22  
**Severity**: HIGH  
**Status**: Root Cause Identified  

---

## Bug Description

Running a correlation or multivariate analysis with a mix of numeric and categorical columns raises a backend exception:

```
TypeError: could not convert string to float: '[1] Before'
```

The stack trace points into the backend multivariate pipeline and appears whenever any selected predictor/response column contains string values such as `"[1] Before"`.

### User Reproduction

1. Upload dataset containing categorical columns with string labels (e.g., `"Before"`, `"After"`).
2. On the Configuration page, select a subset that mixes numeric and categorical columns.
3. Run **Correlation** analysis → request fails with the TypeError above.
4. Switch to **Multivariate** analysis with same column set → identical failure.

---

## Impact

- **User Impact**: Analysis requests fail for the most common scenario (mixed data types). Users cannot complete correlation or multivariate workflows.
- **Data Impact**: No partial results are returned; the entire analysis aborts and the UI displays the exception dump.
- **Scope**: Any dataset where at least one selected column is non-numeric (object dtype) triggers the issue.

---

## Root Cause Analysis

### Correlation Pipeline
- **File**: `backend/relat_ai/services/analysis/pairwise.py`
- The pipeline correctly handles mixed datatypes by coercing numeric columns via `pd.to_numeric(..., errors="coerce")` and using contingency tables for categorical pairs.
- **Status**: No crash observed in the code path; correlation failures stem from the same exception bubbling up from shared preprocessing executed prior to pairwise computations.

### Multivariate Pipeline (Failure Source)
- **File**: `backend/relat_ai/services/analysis/multivariate.py` line ~646 (`_drop_low_variance`).
- `RegressionPlan` builds configs that include every selected predictor regardless of dtype.
- `_drop_low_variance` blindly calls `matrix.var(axis=0)` on the raw predictor frame. When predictors include string/object columns, pandas attempts to cast them to float internally and raises `TypeError: could not convert string to float`.
- Subsequent steps (`statsmodels.OLS`, `_residualize`, PLS) also require purely numeric inputs, so even if `var` handled objects, model fitting would still explode later.

### Shared Preprocessing
- Both correlation and multivariate requests flow through `_resolve_configuration` → `apply_configuration_to_frame` (which returns the raw subset) before dispatching to the specific analysis. No encoding or filtering is applied beforehand.
- Because the multivariate code executes first when `analysis_mode == "multivariate"`, the exception is thrown before any correlation-specific computation, explaining why the user observed identical failures for both modes.

### Conclusion
The backend assumes all selected columns for regression-style analyses are numeric. Allowing object/categorical columns without encoding causes low-variance screening to crash. Correlation requests fail because the same dataset is passed into multivariate helper utilities (shared configuration), which choke on string values during preprocessing.

---

## Proposed Fix

1. **Early Validation** (preferred)
   - Enhance `validate_configuration` / `validate_analysis_mode` to ensure multivariate selections include only numeric responses and predictors. Provide a clear error message instructing users to exclude categorical columns or convert them beforehand.
   - For correlation, skip the regression preparation entirely unless the active mode truly requires it.

2. **Robust Preprocessing** (long-term)
   - Introduce automatic encoding (e.g., one-hot or target encoding) for categorical predictors before `_drop_low_variance` and regression fitting.
   - Convert object columns using `pd.get_dummies` or similar and track the mapping for interpretability.

3. **Guard Rails in `_drop_low_variance`**
   - Filter to numeric dtypes prior to variance computation: `matrix = matrix.select_dtypes(include=[np.number])`.
   - Log warnings for dropped non-numeric predictors so users understand why columns were excluded.

4. **User Feedback**
   - Surface a friendly Streamlit error explaining that multivariate analysis currently requires numeric inputs, listing offending columns.

---

## Next Steps

- [ ] Update validators to block multivariate runs with non-numeric predictors until robust encoding is implemented.
- [ ] Patch `_drop_low_variance` to operate on numeric columns only (defensive fix).
- [ ] Add integration test covering mixed column datasets for both correlation and multivariate modes.
- [ ] Document the numeric-only requirement in user guides until encoding support ships.

---

**Investigated By**: GitHub Copilot  
**Date**: 2025-10-22  
**Status**: Investigation complete; fixes pending
