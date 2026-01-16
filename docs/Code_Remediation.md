# Code Review & Remediation Plan: RelatAI

- **Date:** 2025-11-20
- **Reviewer:** Gemini (Gareth's AI Partner)
- **Target Repo:** `relatai`
- **Status:** Actionable

---

## Part 1: Code Review Findings

### 1. Executive Summary
**Verdict:** The repository achieves the **functional** goal of a self-service analytics prototype, but currently fails the **operational** goal required for a "Quality Event/CAPA" tool in a medical device context.

The code is clean, readable, and well-structured, but the decision to keep the **Audit Trail in-memory** is a critical failure point. In a regulated environment, if it isn't documented (and persisted), it didn't happen.

### 2. Critical Issues (The "Must Fixes")

#### A. The "Ghost" Audit Trail (`backend/relat_ai/services/audit_trail.py`)
* **The Issue:** The file explicitly states it is an `In-memory audit trail store`.
* **Why it matters:** This tool is for "rapid statistical triage during quality events" (per `REPO_PROFILE.md`). If the server restarts, the audit trail vanishes, destroying traceability.
* **Required Fix:** Implement persistence immediately (SQLite recommended for single-node prototype).

#### B. Dangerous File Writes (`backend/relat_ai/services/registry_state.py`)
* **The Issue:** `save_registry_state` uses `path.write_text(...)` directly.
* **Why it matters:** If the disk fills up or the process crashes mid-write, `registry.json` becomes corrupted, resulting in total data loss.
* **Required Fix:** Use an atomic write pattern (write to temp file -> atomic rename).

### 3. Implementation Feedback

#### `backend/relat_ai/services/analysis/auto_triage.py`
* **Strengths:** Statistical logic (CUSUM/PELT, PCA) is sound.
* **Risks:**
    * **Data Nutrition:** Median imputation happens *before* scaling. This can mask "Not Detected" errors (NaNs) common in diagnostic devices.
    * **Signal Normalization:** `SignalVector.normalize` uses `np.searchsorted` on the population. If `all_signals` contains NaNs/Infs, this may throw unexpected results.

#### `backend/relat_ai/services/analysis_runner.py`
* **Caching Logic:** `_build_cache_key` relies on string representations of dictionaries (`SignatureBuilder`), which is fragile. Deterministic JSON serialization is safer.
* **Architecture:** Separation between `runner`, `services`, and `core` is excellent.

---

## Part 2: Remediation Plan

- **Priority:** Correctness > Clarity > Speed
- **Objective:** Address critical safety and persistence issues to make the tool viable for regulated prototyping.

### Phase 1: Persistence & Safety (Immediate Priority)

#### Task 1: Fix the "Ghost" Audit Trail
**Goal:** Persist audit logs to a local SQLite database (`audit.db`).
**Target File:** `backend/relat_ai/services/audit_trail.py`

> **Status:** ✅ Implemented (2026-01-15)
>
> - Added `audit_db_path` setting to `core/config.py`
> - Rewrote `AuditTrailStore` to use SQLite with thread-safe connections
> - Added `set_audit_db_path()` for test isolation
> - Updated `reset_audit_trail()` with `clear_data` parameter
> - Unit tests: `tests/unit/test_audit_trail.py` (9 tests passing)

**Implementation Reference:**
```python
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from relat_ai.core.models import AuditActionModel, AuditLogModel

# Define DB Path (in a real app, config this)
DB_PATH = Path("backend/audit.db")

def _get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def _init_db():
    """Run this on startup."""
    with _get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                dataset_id TEXT PRIMARY KEY,
                dataset_name TEXT,
                dataset_hash TEXT,
                row_count INTEGER,
                column_count INTEGER,
                created_at TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS audit_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id TEXT,
                action_type TEXT,
                details TEXT,
                col_name TEXT,
                timestamp TEXT,
                FOREIGN KEY(dataset_id) REFERENCES audit_logs(dataset_id)
            )
        """)

# NOTE: You will need to refactor AuditTrailStore to use _get_connection() 
# and SQL queries instead of the self._logs dictionary.

```

#### Task 2: Atomic File Writes
**Goal:** Prevent registry.json corruption. Target File: backend/relat_ai/services/registry_state.py

> **Status:** ✅ Implemented (2026-01-15)
>
> - Uses `tempfile.mkstemp()` + `os.replace()` for atomic writes
> - Cleanup of temp files on failure
> - Unit tests: `tests/unit/test_registry_state.py` (7 tests passing)

**Implementation Reference:**
```python
import os
import json
from pathlib import Path
from collections.abc import Sequence
import logging

# Ensure 'os' is imported
def save_registry_state(path: Path, entries: Sequence[RegistryStateEntry], *, logger: logging.Logger | None = None) -> bool:
    payload = json.dumps([
        {
            "metadata": _serialize_metadata(entry.metadata),
            "profile": _serialize_profile(entry.profile),
        }
        for entry in entries
    ])

    # 1. Write to a temp file in the same directory (ensures same filesystem)
    temp_path = path.with_suffix(".tmp") 
    
    try:
        temp_path.write_text(payload, encoding="utf-8")
        # 2. Atomic replacement
        temp_path.replace(path)
    except OSError as exc:
        if logger:
            logger.warning("Unable to persist dataset registry: %s", exc)
        # Cleanup if failed
        if temp_path.exists():
            os.remove(temp_path)
        return False

    return True

```

### Phase 2: Analytic Robustness

#### Task 3: Strict Imputation Control
**Goal:** Fail safely if critical quality data is missing, rather than guessing via median imputation. **Target File:** backend/relat_ai/services/analysis/auto_triage.py

> **Status:** ✅ Implemented (2026-01-15)
>
> - Added `strict_missingness: bool = False` to `AutoTriageConfig`
> - `_prepare_numeric_matrix()` raises `ValueError` when threshold exceeded in strict mode
> - Default is `False` for backwards compatibility
> - Unit tests: `TestStrictMissingness` in `test_analysis_auto_triage.py` (3 tests passing)

**Implementation Reference:**
```python
@dataclass(slots=True)
class AutoTriageConfig:
    # ... existing fields ...
    strict_missingness: bool = False  # New flag

def _prepare_numeric_matrix(frame: pd.DataFrame, config: AutoTriageConfig) -> tuple[pd.DataFrame, dict[str, float]]:
    numeric = frame.loc[:, config.numeric_columns].apply(pd.to_numeric, errors="coerce")
    missing_ratio = numeric.isna().mean().to_dict()

    # CRITICAL CHECK
    if config.strict_missingness:
        failures = [col for col, ratio in missing_ratio.items() if ratio > config.high_missing_threshold]
        if failures:
            raise ValueError(f"Data Quality Failure: Columns {failures} exceed missingness limit in strict mode.")

    # ... proceed with imputation ...

```

#### Task 4: Safe Signal Normalization
**Goal:** Prevent crashes when signals are NaN or Inf. Target File: backend/relat_ai/services/analysis/auto_triage.py

> **Status:** ✅ Implemented (2026-01-15)
>
> - `SignalVector.normalize()` now filters out NaN/Inf values via `np.isfinite()`
> - Returns 0.0 for non-finite input values
> - Unit tests: `TestSignalVectorNormalize` in `test_analysis_auto_triage.py` (4 tests passing)

**Implementation Reference:**
```python
def normalize(self, all_signals: dict[str, dict[str, float]]) -> None:
    for signal_kind in {kind for signals in all_signals.values() for kind in signals}:
        # ... 
        # Extract and sanitize population
        raw_pop = [signals.get(signal_kind, 0.0) for signals in all_signals.values()]
        population = np.array(raw_pop)
        
        # Filter out NaNs and Infs
        population = population[np.isfinite(population)]

        if population.size == 0 or float(population.max()) == 0:
            self.normalized_signals[signal_kind] = 0.0
            continue
        # ...

```

### Phase 3: Infrastructure Hygiene

#### Task 5: Deterministic Caching
**Goal:** Ensure consistent cache keys regardless of dictionary key order. Target File: backend/relat_ai/services/analysis_runner.py

> **Status:** ✅ Already Implemented
>
> Upon review (2026-01-15), `SignatureBuilder` in `backend/relat_ai/services/results.py` already uses
> `json.dumps(..., sort_keys=True)` for deterministic serialization. The `_build_cache_key` function
> in `analysis_runner.py` delegates to `SignatureBuilder`, so no code change is required.

**Implementation Reference:**
```python
import json

def _build_cache_key(...):
    # Use sorted JSON dumping instead of custom string building
    config_sig = json.dumps(configuration.model_dump(), sort_keys=True)
    filters_sig = json.dumps(configuration.filters, sort_keys=True)
    # ...

```

