# Milestone 9 Detailed Implementation Plan: Frontend Experience - Streamlit Prototype

**Version:** 1.0  
**Created:** 2025-01-14  
**Milestone:** M9 - Frontend Experience (Streamlit Prototype)  
**Estimated Effort:** 7-10 days  
**Status:** Planning Phase

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Architecture & Design Philosophy](#architecture--design-philosophy)
4. [Phased Implementation Plan](#phased-implementation-plan)
5. [Component Specifications](#component-specifications)
6. [Visual Design Mockups](#visual-design-mockups)
7. [API Integration Strategy](#api-integration-strategy)
8. [Testing Strategy](#testing-strategy)
9. [Risk Assessment](#risk-assessment)
10. [Success Criteria](#success-criteria)

---

## Executive Summary

### Objective
Deliver a fully functional Streamlit-based prototype frontend that connects users to the RelatAI backend analysis engine, enabling self-service statistical triage through an intuitive interface supporting three analysis modes (Correlation, Multivariate, Auto-Triage).

### Scope
- **In Scope:**
  - Complete dataset upload and configuration workflow
  - Three analysis mode interfaces (Correlation, Multivariate, Auto-Triage)
  - Interactive visualizations (heatmaps, network graphs, tables, charts)
  - Template save/load functionality
  - Configuration preview and filtering
  - AI summary display (placeholder/mock initially)
  - Export capabilities (results, reduced datasets)
  - Confidence flag indicators
  - Audit trail viewer

- **Out of Scope:**
  - Production-grade React/Dash migration
  - User authentication/authorization
  - Multi-user session management
  - Advanced animation/transitions
  - Real-time collaborative editing

### Key Design Principles
1. **Progressive Disclosure:** Simple defaults with advanced options hidden until needed
2. **Immediate Feedback:** Show processing status, preview data changes instantly
3. **Guided Workflow:** Clear steps from upload → configure → analyze → interpret
4. **Visual Hierarchy:** Most important information prominent, secondary details collapsible
5. **Graceful Degradation:** Handle missing data, API errors, and edge cases elegantly

---

## Current State Analysis

### Existing Assets
✅ **Backend API:**
- Dataset upload/retrieval (`/datasets`)
- Configuration management (`/datasets/{id}/configuration`)
- Template operations (`/datasets/{id}/templates`)
- Audit trail access (`/audit`)
- Health checks (`/health`)

❌ **Missing Backend Components:**
- Analysis execution endpoint (`POST /datasets/{id}/analyze`)
- Result retrieval endpoint (`GET /datasets/{id}/results`)
- Export endpoint (`POST /datasets/{id}/export`)

✅ **Minimal Streamlit Shell:**
- Basic upload widget
- Page configuration
- No API integration

✅ **Visualization Utilities:**
- Heatmap metadata builder
- Network graph structures
- Limited to correlation mode

### Gap Analysis

| Component | Backend Status | Frontend Status | Priority |
|-----------|---------------|-----------------|----------|
| Dataset Upload | ✅ Complete | ⚠️ Basic shell | HIGH |
| Configuration UI | ✅ API Ready | ❌ Not started | HIGH |
| Analysis Execution | ❌ No endpoint | ❌ Not started | **CRITICAL** |
| Correlation Viz | ⚠️ Partial | ❌ Not started | HIGH |
| Multivariate Viz | ⚠️ Partial | ❌ Not started | HIGH |
| Auto-Triage Viz | ✅ Backend ready | ❌ Not started | MEDIUM |
| Templates | ✅ Complete | ❌ Not started | MEDIUM |
| Export | ❌ No endpoint | ❌ Not started | LOW |

**Critical Blocker:** Analysis execution endpoint must be implemented before frontend can trigger analyses.

---

## Architecture & Design Philosophy

### Application Structure

```
streamlit_app/
├── app.py                          # Main entry point, page routing
├── config.py                       # Backend API URLs, settings
├── pages/
│   ├── 1_📊_Dataset_Upload.py     # Upload and initial profiling
│   ├── 2_⚙️_Configuration.py       # Column selection, filtering, mode
│   ├── 3_🔬_Analysis.py            # Execute analysis, view results
│   └── 4_📋_Templates.py           # Manage saved configurations
├── components/
│   ├── __init__.py
│   ├── upload.py                   # Upload widget with validation
│   ├── column_selector.py          # Multi-select with search
│   ├── filter_panel.py             # Dynamic filter builder
│   ├── mode_selector.py            # Analysis mode toggle
│   ├── correlation_view.py         # Correlation results display
│   ├── multivariate_view.py        # Multivariate results display
│   ├── auto_triage_view.py         # Auto-triage results display
│   ├── visualizations.py           # Chart rendering functions
│   ├── confidence_flags.py         # Flag indicator components
│   ├── audit_viewer.py             # Audit trail display
│   └── export_controls.py          # Export button and options
├── utils/
│   ├── __init__.py
│   ├── api_client.py               # Backend API wrapper
│   ├── session_state.py            # State management helpers
│   ├── formatters.py               # Data formatting utilities
│   └── validators.py               # Input validation
└── assets/
    ├── styles.css                  # Custom CSS overrides
    └── logo.png                    # Application logo
```

### State Management Strategy

**Streamlit Session State Keys:**
```python
{
    # Dataset tracking
    "current_dataset_id": str | None,
    "dataset_metadata": dict | None,
    "dataset_profile": dict | None,
    
    # Configuration state
    "configuration": dict | None,
    "preview_data": pd.DataFrame | None,
    "selected_template": str | None,
    
    # Analysis state
    "analysis_mode": "correlation" | "multivariate" | "auto_triage",
    "analysis_running": bool,
    "analysis_results": dict | None,
    "analysis_error": str | None,
    
    # UI state
    "show_advanced_options": bool,
    "visualization_type": str,
    "selected_variables": list[str],
    
    # Cache
    "cached_templates": list[dict],
    "audit_logs": list[dict],
}
```

### API Client Design

```python
# utils/api_client.py
import requests
from typing import Optional
import streamlit as st

class RelatAIClient:
    """Backend API client with error handling and caching."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    # Dataset operations
    def upload_dataset(self, file, filename: str) -> dict:
        """Upload dataset and return metadata."""
        
    def get_dataset(self, dataset_id: str) -> dict:
        """Retrieve dataset metadata and profile."""
    
    # Configuration operations
    def get_configuration(self, dataset_id: str) -> dict:
        """Get current configuration for dataset."""
    
    def update_configuration(self, dataset_id: str, updates: dict) -> dict:
        """Update configuration options."""
    
    def preview_configuration(self, dataset_id: str, limit: int = 50) -> dict:
        """Preview filtered dataset."""
    
    # Template operations
    def list_templates(self, dataset_id: str) -> list[dict]:
        """List all templates for dataset."""
    
    def create_template(self, dataset_id: str, name: str, 
                       description: str, config: Optional[dict] = None) -> dict:
        """Create new configuration template."""
    
    def apply_template(self, dataset_id: str, template_id: str) -> dict:
        """Apply template to dataset configuration."""
    
    # Analysis operations (TO BE IMPLEMENTED IN BACKEND)
    def run_analysis(self, dataset_id: str, mode: str, 
                     parameters: Optional[dict] = None) -> dict:
        """Execute analysis and return results."""
    
    def get_results(self, dataset_id: str, result_id: str) -> dict:
        """Retrieve cached analysis results."""
    
    # Audit operations
    def get_audit_logs(self, dataset_id: Optional[str] = None) -> list[dict]:
        """Retrieve audit trail entries."""
    
    # Export operations (TO BE IMPLEMENTED IN BACKEND)
    def export_reduced_dataset(self, dataset_id: str, 
                               top_n: int, 
                               include_columns: list[str]) -> bytes:
        """Export reduced dataset as CSV."""
```

---

## Phased Implementation Plan

### Phase 1: Foundation & Upload (Days 1-2)
**Goal:** Establish architecture and complete dataset upload workflow

**Tasks:**
1. **Project Structure Setup** (2 hours)
   - Create directory structure
   - Set up `config.py` with backend URL configuration
   - Create `api_client.py` skeleton
   - Initialize component modules

2. **API Client Implementation** (4 hours)
   - Implement dataset upload/retrieval methods
   - Add configuration management methods
   - Include error handling and retry logic
   - Add response caching

3. **Enhanced Upload Page** (4 hours)
   - File upload with validation (CSV/Excel/Parquet)
   - Progress indicator during upload
   - Display dataset profile after upload
   - Show column types, statistics, missing data
   - Navigate to configuration page on success

4. **Session State Management** (2 hours)
   - Create state initialization helpers
   - Implement state persistence patterns
   - Add state debugging utilities (dev mode)

5. **Basic Styling** (2 hours)
   - Custom CSS for consistent look
   - Color scheme selection
   - Typography and spacing standards
   - Responsive layout foundations

**Deliverables:**
- ✅ Functional upload workflow
- ✅ Dataset profile display
- ✅ API client with dataset operations
- ✅ Session state framework

**Success Metrics:**
- Upload 5MB CSV in < 10 seconds
- Profile displays correctly for all column types
- Session state persists across page navigation

---

### Phase 2: Configuration Interface (Days 3-4)
**Goal:** Build comprehensive configuration UI with preview

**Tasks:**
1. **Column Selector Component** (4 hours)
   - Multi-select with all columns pre-selected
   - Search/filter capability
   - Group by data type
   - Show column statistics on hover
   - Anchor column designation

2. **Filter Panel Component** (6 hours)
   - Dynamic filter builder (add/remove filters)
   - Type-aware filter inputs:
     - Numeric: range sliders, min/max
     - Categorical: multi-select dropdown
     - Date: date range picker
   - Filter preview (show row count impact)
   - Clear all filters button

3. **Mode Selector Component** (2 hours)
   - Radio buttons/tabs for three modes
   - Mode descriptions with tooltips
   - Show/hide mode-specific parameters:
     - Correlation: threshold settings
     - Multivariate: max variables, interaction depth, anchors
     - Auto-Triage: clustering params, change-point sensitivity

4. **Configuration Preview** (4 hours)
   - Live data preview table (first 50 rows)
   - Row/column count after filters
   - Quick statistics summary
   - Refresh on configuration change

5. **Template Management** (4 hours)
   - Save current configuration as template
   - Load template dropdown
   - Apply template to configuration
   - Delete template (with confirmation)
   - Template description display

**Deliverables:**
- ✅ Column selector with search
- ✅ Dynamic filter panel
- ✅ Mode selector with parameters
- ✅ Live configuration preview
- ✅ Template save/load functionality

**Success Metrics:**
- Filter application reflects in preview < 2 seconds
- Template save/load roundtrip successful
- All three modes display correct parameter inputs

---

### Phase 3: Analysis Execution & Results Display (Days 5-7)
**Goal:** Implement analysis trigger and results visualization

**Tasks:**

#### 3.1 Backend Analysis Endpoint (PREREQUISITE - 4 hours)
**Note:** This must be implemented in backend before frontend work can proceed.

```python
# backend/relat_ai/api/routes/analysis.py
@router.post(
    "/{dataset_id}/analyze",
    response_model=AnalysisResultResponse,
    summary="Execute analysis on configured dataset"
)
async def run_analysis(
    dataset_id: str,
    mode: AnalysisMode,
    parameters: Optional[AnalysisParameters] = None
) -> AnalysisResultResponse:
    """
    Execute correlation, multivariate, or auto-triage analysis.
    Returns structured results with visualizations and insights.
    """
    # Load dataset and configuration
    # Run appropriate analysis pipeline
    # Store results in cache
    # Return serialized result
```

#### 3.2 Analysis Page Shell (2 hours)
- "Run Analysis" button with confirmation
- Progress spinner during execution
- Error display with retry option
- Results tabs: Overview | Details | Visualizations | Insights

#### 3.3 Correlation Results View (6 hours)
- **Ranked Correlation Table**
  - Sortable columns (strength, p-value, method)
  - Pagination (50 rows per page)
  - Confidence flags as colored badges
  - Expand row for details
  
- **Correlation Heatmap**
  - Plotly heatmap with hover details
  - Color scale selection
  - Download as PNG/SVG
  
- **Network Graph**
  - Force-directed graph (plotly/networkx)
  - Node size by degree
  - Edge thickness by correlation strength
  - Interactive zoom/pan

#### 3.4 Multivariate Results View (6 hours)
- **Model Summary Table**
  - Response variable
  - Predictors (including interactions)
  - R², adjusted R², AIC, BIC
  - Effect sizes and p-values
  
- **Coefficient Plot**
  - Bar chart of standardized coefficients
  - Error bars (confidence intervals)
  - Highlight significant terms
  
- **Diagnostics Display**
  - VIF table (collinearity check)
  - Residual plots (if available)
  - ANOVA table (if applicable)

#### 3.5 Auto-Triage Results View (6 hours)
- **Suspicion Ranking Table**
  - Top variables by contribution
  - Anomaly score
  - Confidence level
  
- **PCA Biplot**
  - Scatter plot of first 2 components
  - Loadings vectors overlay
  - Variance explained labels
  
- **Change-Point Chart**
  - Time series with detected change points
  - Magnitude and direction indicators
  - Confidence bands
  
- **Cluster Visualization**
  - 2D projection of clusters (t-SNE/PCA)
  - Color by cluster assignment
  - Cluster statistics sidebar

#### 3.6 Confidence Flags Component (2 hours)
- Badge styling (warning, info, error levels)
- Tooltip with detailed explanation
- Aggregate flag summary at top of results
- Filter results by flag type

#### 3.7 AI Summary Display (2 hours - MOCK INITIALLY)
- Collapsible summary section
- Narrative text with formatting
- Links to referenced visualizations
- Confidence references highlighted
- Placeholder for future LLM integration

**Deliverables:**
- ✅ Analysis execution with progress tracking
- ✅ Correlation results with table, heatmap, network
- ✅ Multivariate results with coefficients and diagnostics
- ✅ Auto-triage results with rankings, PCA, change-points
- ✅ Confidence flag indicators
- ✅ AI summary placeholder

**Success Metrics:**
- Analysis completes within performance targets (5s/60s/90s)
- All visualizations render in < 10 seconds
- Results persist across page refresh
- Confidence flags display correctly

---

### Phase 4: Polish & Advanced Features (Days 8-9)
**Goal:** Add export, audit trail, and UX enhancements

**Tasks:**

1. **Export Controls** (4 hours)
   - Export full results as JSON
   - Export reduced dataset (top-N variables)
   - Export visualizations as images
   - Download audit trail as CSV
   - Format selection (CSV, Excel, JSON)

2. **Audit Trail Viewer** (4 hours)
   - Dedicated audit page
   - Timeline view of preprocessing actions
   - Filter by dataset, action type, date
   - Expandable detail for each action
   - Export audit log

3. **Advanced Configuration Options** (3 hours)
   - Collapsible "Advanced Settings" section
   - Preprocessing controls:
     - Imputation strategy
     - Outlier handling
     - Scaling method
   - Performance settings:
     - Sample size limits
     - Parallel workers
   - Sensitivity thresholds

4. **Help & Documentation** (3 hours)
   - Contextual help tooltips
   - "?" icons with detailed explanations
   - Statistical method descriptions
   - Interpretation guidance
   - Link to full documentation

5. **Error Handling & Validation** (4 hours)
   - Friendly error messages
   - Input validation with inline feedback
   - API error recovery
   - Graceful degradation for missing features
   - Clear call-to-action for resolutions

**Deliverables:**
- ✅ Export functionality (results, datasets, images)
- ✅ Audit trail viewer page
- ✅ Advanced settings panel
- ✅ Comprehensive help system
- ✅ Robust error handling

**Success Metrics:**
- Export operations complete in < 5 seconds
- Audit trail displays 1000+ entries without lag
- All inputs validated before submission
- Error messages actionable and clear

---

### Phase 5: Testing & Documentation (Day 10)
**Goal:** Comprehensive testing and documentation

**Tasks:**

1. **Manual Testing** (3 hours)
   - End-to-end workflow testing (all three modes)
   - Edge case testing (empty datasets, single column, etc.)
   - Cross-browser compatibility (Chrome, Firefox, Edge)
   - Responsive layout testing (desktop, tablet)

2. **Performance Testing** (2 hours)
   - Upload 50k row dataset
   - Apply complex filters (multiple columns)
   - Run analyses and measure response times
   - Verify visualization render times

3. **User Documentation** (3 hours)
   - Create `frontend/streamlit_app/README.md`
   - Workflow guides with screenshots
   - Configuration examples
   - Troubleshooting section

4. **Developer Documentation** (2 hours)
   - Code comments and docstrings
   - Component API documentation
   - State management guide
   - Extending the frontend guide

**Deliverables:**
- ✅ Test results documented
- ✅ User-facing documentation
- ✅ Developer documentation
- ✅ Known issues log

**Success Metrics:**
- All critical workflows tested successfully
- Performance targets met
- Documentation covers common use cases
- Zero critical bugs outstanding

---

## Component Specifications

### 1. Column Selector Component

**Purpose:** Allow users to select/deselect columns for analysis with default all-selected state.

**Features:**
- Multi-select list with search bar
- Group by data type (numeric, categorical, datetime)
- Display column statistics on hover (mean, missing %, unique values)
- "Select All" / "Deselect All" buttons
- Anchor column designation (checkbox or star icon)
- Visual indicator for selected columns
- Column count summary ("45 of 50 columns selected")

**API:**
```python
def column_selector(
    columns: list[dict],  # [{"name": "col1", "type": "numeric", "stats": {...}}]
    selected: list[str],  # Pre-selected column names
    allow_anchors: bool = False,
    key: str = "column_selector"
) -> tuple[list[str], list[str]]:  # (selected_columns, anchor_columns)
    """Render column selector and return selections."""
```

**State Updates:**
- `st.session_state["configuration"]["selected_columns"]`
- `st.session_state["configuration"]["anchor_columns"]`

---

### 2. Filter Panel Component

**Purpose:** Dynamic filter builder for subsetting data by column values.

**Features:**
- Add/remove filter rows
- Column dropdown (only selected columns)
- Type-aware operators:
  - Numeric: `=`, `!=`, `<`, `<=`, `>`, `>=`, `between`, `in`
  - Categorical: `in`, `not in`
  - Date: `before`, `after`, `between`
- Value input widgets:
  - Numeric: number input, range slider
  - Categorical: multi-select dropdown
  - Date: date picker, date range
- Preview row count after filters
- "Clear All Filters" button
- Collapsible section

**API:**
```python
def filter_panel(
    dataset_id: str,
    profile: dict,
    current_filters: dict[str, list],
    key: str = "filter_panel"
) -> dict[str, list]:
    """Render filter panel and return updated filters."""
```

**State Updates:**
- `st.session_state["configuration"]["filters"]`

---

### 3. Mode Selector Component

**Purpose:** Toggle between analysis modes and configure mode-specific parameters.

**Features:**
- Three mode tabs/radio buttons:
  - 🔗 Correlation
  - 📊 Multivariate
  - 🔍 Auto-Triage
- Mode descriptions (expandable)
- Mode-specific parameter inputs:
  - **Correlation:** Correlation threshold slider, method selection
  - **Multivariate:** Max variables (3-10), interaction depth (1-3), anchor selection
  - **Auto-Triage:** Clustering algorithm, change-point sensitivity, PCA components
- Parameter validation and tooltips

**API:**
```python
def mode_selector(
    current_mode: str,
    current_params: dict,
    key: str = "mode_selector"
) -> tuple[str, dict]:  # (mode, parameters)
    """Render mode selector and return mode + parameters."""
```

**State Updates:**
- `st.session_state["analysis_mode"]`
- `st.session_state["configuration"]["analysis_mode"]`
- `st.session_state["configuration"]["max_variables"]`
- `st.session_state["configuration"]["interaction_depth"]`

---

### 4. Correlation View Component

**Purpose:** Display correlation analysis results with multiple visualization options.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Correlation Analysis Results                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📊 Overview                                             │ │
│ │ • Total Pairs Analyzed: 1,234                          │ │
│ │ • Significant Correlations (p < 0.05): 567 (45.9%)    │ │
│ │ • Strong Correlations (|r| > 0.7): 89 (7.2%)          │ │
│ │ • Confidence Flags: 12 warnings, 3 low-n flags        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Visualization Type: [Heatmap] [Network] [Table]        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [VISUALIZATION AREA - Plotly Interactive Chart]             │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Top Correlations                                        │ │
│ │ ┌────────────────┬──────┬────────┬──────┬─────────────┐│ │
│ │ │ Variable Pair  │  r   │p-value │  n   │   Flags     ││ │
│ │ ├────────────────┼──────┼────────┼──────┼─────────────┤│ │
│ │ │ temp vs press  │ 0.92 │< 0.001 │ 5000 │ [Strong]    ││ │
│ │ │ humidity vs ... │-0.78 │< 0.001 │ 4850 │ [Negative]  ││ │
│ │ └────────────────┴──────┴────────┴──────┴─────────────┘│ │
│ │ [Show More] [Export CSV]                                │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**API:**
```python
def correlation_view(
    results: dict,
    key: str = "correlation_view"
) -> None:
    """Render correlation results with visualizations."""
```

---

### 5. Multivariate View Component

**Purpose:** Display multivariate analysis results (regression, ANOVA, PLS).

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Multivariate Analysis Results                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📈 Model Summary                                        │ │
│ │ • Response: Sales Revenue                              │ │
│ │ • Predictors: Price, Promotion, Seasonality (+ 2 int.) │ │
│ │ • R² = 0.85, Adjusted R² = 0.83                        │ │
│ │ • F(5, 494) = 558.2, p < 0.001                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Coefficient Estimates                                   │ │
│ │ ┌──────────────┬─────────┬─────────┬────────┬─────────┐│ │
│ │ │ Predictor    │   β     │  Std.Err│p-value │  VIF    ││ │
│ │ ├──────────────┼─────────┼─────────┼────────┼─────────┤│ │
│ │ │ Price        │ -0.65** │  0.08   │< 0.001 │  1.8    ││ │
│ │ │ Promotion    │  0.42** │  0.06   │< 0.001 │  1.2    ││ │
│ │ │ Price × Prom │  0.18*  │  0.09   │  0.04  │  2.3    ││ │
│ │ └──────────────┴─────────┴─────────┴────────┴─────────┘│ │
│ │ * p < 0.05, ** p < 0.01                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [COEFFICIENT PLOT - Bar Chart with Error Bars]              │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ⚠️ Diagnostics & Quality Flags                          │ │
│ │ • Collinearity Warning: Price × Promotion (VIF = 2.3)  │ │
│ │ • Model fit excellent (R² > 0.8)                        │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**API:**
```python
def multivariate_view(
    results: dict,
    key: str = "multivariate_view"
) -> None:
    """Render multivariate analysis results."""
```

---

### 6. Auto-Triage View Component

**Purpose:** Display unsupervised triage results (PCA, change-points, clustering).

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Auto-Triage Results                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🔍 Suspicion Ranking                                    │ │
│ │ ┌────────┬──────────────────────┬────────┬────────────┐│ │
│ │ │ Rank   │ Variable             │ Score  │ Reason     ││ │
│ │ ├────────┼──────────────────────┼────────┼────────────┤│ │
│ │ │   1    │ Instrument_ID        │  0.89  │ Clustering ││ │
│ │ │   2    │ Batch_Temperature    │  0.82  │ Change-Pt  ││ │
│ │ │   3    │ Operator_Shift       │  0.76  │ Residuals  ││ │
│ │ └────────┴──────────────────────┴────────┴────────────┘│ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌───────────────────────┬─────────────────────────────────┐ │
│ │ PCA Biplot            │ Change-Point Detection          │ │
│ │ [SCATTER PLOT]        │ [TIME SERIES WITH MARKERS]      │ │
│ │ PC1 vs PC2            │ Detected: 3 change points       │ │
│ │ 65% variance          │ Confidence: High                │ │
│ └───────────────────────┴─────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Cluster Summary                                         │ │
│ │ • Algorithm: K-Means (k=4)                              │ │
│ │ • Silhouette Score: 0.68                                │ │
│ │ • Cluster 2: 78 anomalous samples (15.6%)               │ │
│ │ [CLUSTER SCATTER PLOT]                                  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**API:**
```python
def auto_triage_view(
    results: dict,
    key: str = "auto_triage_view"
) -> None:
    """Render auto-triage analysis results."""
```

---

## Visual Design Mockups

### Color Scheme Options

**Option A: Professional Blue (Recommended)**
- Primary: `#1E3A8A` (Dark Blue)
- Secondary: `#3B82F6` (Blue)
- Accent: `#10B981` (Green)
- Warning: `#F59E0B` (Amber)
- Error: `#EF4444` (Red)
- Background: `#F9FAFB` (Light Gray)
- Text: `#111827` (Near Black)

**Option B: Scientific Purple**
- Primary: `#7C3AED` (Purple)
- Secondary: `#A78BFA` (Light Purple)
- Accent: `#06B6D4` (Cyan)
- Warning: `#FBBF24` (Yellow)
- Error: `#DC2626` (Red)
- Background: `#FAFAFA` (Off White)
- Text: `#1F2937` (Dark Gray)

**Option C: Minimalist Green**
- Primary: `#059669` (Emerald)
- Secondary: `#34D399` (Light Green)
- Accent: `#6366F1` (Indigo)
- Warning: `#F97316` (Orange)
- Error: `#B91C1C` (Dark Red)
- Background: `#FFFFFF` (White)
- Text: `#0F172A` (Slate)

### Layout Mockup: Main Dashboard

```
┌──────────────────────────────────────────────────────────────────┐
│ [LOGO] RelatAI                      [Help] [Settings] [Profile]  │
├──────────────────────────────────────────────────────────────────┤
│ ┌─ Sidebar ──────────┐ ┌─ Main Content ─────────────────────┐   │
│ │                    │ │                                     │   │
│ │ 📊 Dashboard       │ │  Welcome to RelatAI                 │   │
│ │ ➤ Upload Dataset   │ │                                     │   │
│ │   Configure        │ │  Recent Datasets:                   │   │
│ │   Analyze          │ │  ┌────────────────────────────────┐│   │
│ │   Templates        │ │  │ Sales_Q4_2024.csv              ││   │
│ │   Audit Trail      │ │  │ 48,529 rows × 23 columns       ││   │
│ │                    │ │  │ Last analyzed: 2 hours ago     ││   │
│ │ ──────────────     │ │  │ [Open] [Delete]                ││   │
│ │ Current Dataset:   │ │  └────────────────────────────────┘│   │
│ │ Sales_Q4_2024.csv  │ │                                     │   │
│ │ ⚙️ Configured      │ │  ┌────────────────────────────────┐│   │
│ │ ✓ 18/23 columns    │ │  │ Quality_Event_Jan.xlsx         ││   │
│ │ ✓ 3 filters active │ │  │ 12,045 rows × 15 columns       ││   │
│ │                    │ │  │ Last analyzed: 1 day ago       ││   │
│ │ [Run Analysis]     │ │  │ [Open] [Delete]                ││   │
│ │                    │ │  └────────────────────────────────┘│   │
│ │ ──────────────     │ │                                     │   │
│ │ Quick Actions:     │ │  Quick Start Guide:                 │   │
│ │ • Upload new       │ │  1. Upload your dataset             │   │
│ │ • Load template    │ │  2. Configure columns and filters   │   │
│ │ • View audit log   │ │  3. Select analysis mode            │   │
│ │                    │ │  4. Run analysis                    │   │
│ │                    │ │  5. Interpret results               │   │
│ └────────────────────┘ └─────────────────────────────────────┘   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Mockup: Configuration Page

```
┌──────────────────────────────────────────────────────────────────┐
│ ← Back to Dashboard                      [Save Template] [Help]  │
├──────────────────────────────────────────────────────────────────┤
│ Configure: Sales_Q4_2024.csv                                     │
│                                                                   │
│ ┌─ Column Selection ───────────────────────────────────────────┐│
│ │ Search columns: [_____________] [Select All] [Clear All]     ││
│ │                                                               ││
│ │ ✓ Numeric (12 selected)        ✓ Categorical (4 selected)   ││
│ │   ☑ Sales_Amount                 ☑ Region                    ││
│ │   ☑ Units_Sold                   ☑ Product_Category          ││
│ │   ☑ Price                        ☑ Customer_Segment          ││
│ │   ☑ Discount                     ☑ Sales_Channel             ││
│ │   ☑ Cost_of_Goods                                            ││
│ │   ☑ Profit_Margin              ☐ Date (2 selected)           ││
│ │   ... [Expand]                   ☑ Order_Date                ││
│ │                                  ☑ Ship_Date                 ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ ┌─ Filters ────────────────────────────────────────────────────┐│
│ │ [+ Add Filter]                                                ││
│ │                                                               ││
│ │ Filter 1: Region        [in]      [Europe, North America] ×  ││
│ │ Filter 2: Sales_Amount  [>=]      [1000]                   ×  ││
│ │ Filter 3: Order_Date    [between] [2024-01-01 to 2024-12-31]×││
│ │                                                               ││
│ │ Preview: 38,429 rows (79.2% of dataset)    [Clear All]       ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ ┌─ Analysis Mode ──────────────────────────────────────────────┐│
│ │ ⚪ Correlation  ⚫ Multivariate  ⚪ Auto-Triage                ││
│ │                                                               ││
│ │ Multivariate Parameters:                                      ││
│ │ • Max Variables: [5]  slider (3────●────10)                  ││
│ │ • Interaction Depth: [2]  ⚪ None ⚫ 2-way ⚪ 3-way            ││
│ │ • Anchor Variables: [Sales_Amount, Price]                    ││
│ │                                                               ││
│ │ ▼ Advanced Settings (click to expand)                        ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ ┌─ Configuration Preview ──────────────────────────────────────┐│
│ │ Showing first 50 rows after filters                          ││
│ │ ┌──────────┬──────────┬────────┬─────────────┬─────────────┐││
│ │ │ Region   │ Sales_$ │ Units  │ Product_Cat │ Order_Date  │││
│ │ ├──────────┼──────────┼────────┼─────────────┼─────────────┤││
│ │ │ Europe   │ 1,250   │  5     │ Electronics │ 2024-01-15  │││
│ │ │ N.America│ 3,480   │ 12     │ Furniture   │ 2024-01-18  │││
│ │ │ ...      │ ...     │ ...    │ ...         │ ...         │││
│ │ └──────────┴──────────┴────────┴─────────────┴─────────────┘││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ [← Previous: Upload] [Next: Analyze →]                           │
└──────────────────────────────────────────────────────────────────┘
```

### Interactive Prototype Suggestion

**Recommendation:** Create a simple interactive HTML mockup using:
- **Figma** (free tier) for static mockups
- **Streamlit Cloud** for live prototype demos
- **Miro/Excalidraw** for wireframes

**Deliverable:** `docs/mockups/` directory with:
- `dashboard.png` - Main dashboard layout
- `upload.png` - Upload page design
- `configure.png` - Configuration interface
- `results_correlation.png` - Correlation results view
- `results_multivariate.png` - Multivariate results view
- `results_autotriage.png` - Auto-triage results view
- `interactive_demo.html` - Clickable prototype (optional)

---

## API Integration Strategy

### Backend Endpoints Required

**Existing (Ready to Use):**
- ✅ `POST /datasets` - Upload dataset
- ✅ `GET /datasets/{id}` - Retrieve dataset metadata
- ✅ `GET /datasets/{id}/configuration` - Get configuration
- ✅ `PATCH /datasets/{id}/configuration` - Update configuration
- ✅ `GET /datasets/{id}/configuration/preview` - Preview filtered data
- ✅ `POST /datasets/{id}/templates` - Create template
- ✅ `GET /datasets/{id}/templates` - List templates
- ✅ `GET /datasets/{id}/templates/{template_id}` - Get template
- ✅ `POST /datasets/{id}/templates/{template_id}/apply` - Apply template
- ✅ `DELETE /datasets/{id}/templates/{template_id}` - Delete template
- ✅ `GET /audit/` - List all audit logs
- ✅ `GET /audit/{dataset_id}` - Get dataset audit log

**Missing (Must Be Implemented):**
- ❌ `POST /datasets/{id}/analyze` - Execute analysis
- ❌ `GET /datasets/{id}/results` - Retrieve results
- ❌ `GET /datasets/{id}/results/{result_id}` - Get specific result
- ❌ `POST /datasets/{id}/export` - Export reduced dataset
- ❌ `GET /datasets/{id}/visualizations/{viz_type}` - Get visualization data

### API Request/Response Examples

**1. Run Analysis:**
```http
POST /datasets/{dataset_id}/analyze
Content-Type: application/json

{
  "mode": "multivariate",
  "parameters": {
    "max_variables": 5,
    "interaction_depth": 2,
    "anchor_columns": ["sales_amount", "price"]
  }
}

Response 202 Accepted:
{
  "analysis_id": "abc123",
  "status": "running",
  "estimated_time": 45,
  "message": "Analysis started successfully"
}
```

**2. Get Results:**
```http
GET /datasets/{dataset_id}/results/{analysis_id}

Response 200 OK:
{
  "analysis_id": "abc123",
  "status": "completed",
  "mode": "multivariate",
  "results": {
    "models": [...],
    "ranked_insights": [...],
    "quality_flags": [...],
    "metadata": {...}
  },
  "visualizations": {
    "coefficient_plot": {...},
    "diagnostics": {...}
  },
  "ai_summary": null,
  "completed_at": "2025-01-14T10:30:45Z",
  "duration_seconds": 42
}
```

### Error Handling Strategy

**Frontend Error Categories:**
1. **Network Errors** - API unreachable
   - Display: "Cannot connect to backend. Please check that the server is running."
   - Action: Retry button, check backend status

2. **Validation Errors** (422) - Invalid input
   - Display: Inline form errors with specific field messages
   - Action: Highlight invalid fields, provide correction guidance

3. **Not Found Errors** (404) - Resource missing
   - Display: "Dataset not found. It may have been deleted."
   - Action: Return to dashboard, list available datasets

4. **Processing Errors** (500) - Backend failure
   - Display: "Analysis failed. Please try again or contact support."
   - Action: Retry button, export error details for debugging

5. **Timeout Errors** - Analysis takes too long
   - Display: Progress bar with estimated time
   - Action: Option to cancel, notification when complete

**Implementation:**
```python
# utils/api_client.py
class APIError(Exception):
    """Base API error."""
    def __init__(self, message: str, status_code: int, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

def handle_api_error(error: APIError) -> None:
    """Display user-friendly error message in Streamlit."""
    if error.status_code == 404:
        st.error(f"❌ {error.message}")
        st.info("The requested resource was not found. Please refresh the page.")
    elif error.status_code == 422:
        st.error(f"⚠️ Validation Error")
        for field, message in error.details.items():
            st.warning(f"**{field}:** {message}")
    elif error.status_code >= 500:
        st.error(f"🔥 Server Error: {error.message}")
        with st.expander("Technical Details"):
            st.json(error.details)
    else:
        st.error(f"❌ Error: {error.message}")
```

---

## Testing Strategy

### 1. Unit Testing (Component Level)

**Tools:** `pytest`, `streamlit.testing`

**Test Coverage:**
- API client methods (mock requests)
- State management helpers
- Data formatters and validators
- Component rendering (snapshot tests)

**Example Test:**
```python
# tests/test_api_client.py
def test_upload_dataset_success(mock_requests):
    """Test successful dataset upload."""
    mock_requests.post.return_value.status_code = 201
    mock_requests.post.return_value.json.return_value = {
        "dataset_id": "test123",
        "filename": "test.csv"
    }
    
    client = RelatAIClient("http://localhost:8000")
    result = client.upload_dataset(file=mock_file, filename="test.csv")
    
    assert result["dataset_id"] == "test123"
    assert mock_requests.post.called
```

### 2. Integration Testing (Page Level)

**Tools:** Manual testing with backend running

**Test Cases:**
- Complete workflow: upload → configure → analyze → view results
- Template save/load roundtrip
- Filter application with preview update
- Error recovery scenarios

**Test Plan:**
```markdown
| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| Upload CSV | 1. Navigate to upload page<br>2. Select valid CSV<br>3. Click upload | Profile displays, navigate to config |
| Apply Filter | 1. Add region filter "Europe"<br>2. View preview | Row count decreases, preview shows Europe only |
| Run Correlation | 1. Select correlation mode<br>2. Click analyze<br>3. Wait for completion | Heatmap renders, table shows results |
| Save Template | 1. Configure columns/filters<br>2. Save as "Q4_Analysis"<br>3. Load template on new session | Configuration restored exactly |
```

### 3. End-to-End Testing (User Journey)

**Scenarios:**
1. **Quality Engineer Triage Workflow**
   - Upload quality event dataset
   - Filter to specific date range and lot number
   - Run auto-triage to identify suspicious variables
   - Export top 10 variables for further analysis

2. **Data Analyst EDA Workflow**
   - Upload sales dataset
   - Configure multivariate analysis (sales as response)
   - Add interaction terms for price × promotion
   - Review coefficient plot and VIF diagnostics
   - Save analysis configuration as template

3. **Manager Review Workflow**
   - Open existing dataset
   - Load saved template
   - Run correlation analysis
   - View AI summary (when available)
   - Export results as PDF

### 4. Performance Testing

**Metrics to Measure:**
- Dataset upload time (5MB, 50MB files)
- Configuration preview refresh time
- Visualization render time
- Page load times
- Memory usage with large datasets

**Target Benchmarks:**
| Operation | Target | Maximum Acceptable |
|-----------|--------|-------------------|
| Upload 5MB CSV | < 5s | 10s |
| Apply filter + preview | < 2s | 5s |
| Render heatmap (100 variables) | < 3s | 8s |
| Load analysis results | < 1s | 3s |
| Save template | < 500ms | 2s |

### 5. Cross-Browser Testing

**Browsers:**
- Chrome (primary target)
- Firefox
- Edge
- Safari (if available)

**Test Points:**
- File upload widget compatibility
- Interactive chart interactions
- CSS rendering consistency
- JavaScript execution

---

## Risk Assessment

### Critical Risks

**1. Missing Backend Analysis Endpoint (CRITICAL)**
- **Impact:** Cannot execute analyses from frontend
- **Probability:** HIGH (confirmed missing)
- **Mitigation:** 
  - Implement endpoint as Phase 3 prerequisite
  - Estimate 4-6 hours of backend work
  - Mock endpoint for frontend development in parallel
  - Clear blocker for frontend team

**2. Performance Degradation with Large Datasets**
- **Impact:** Poor user experience, timeouts
- **Probability:** MEDIUM
- **Mitigation:**
  - Implement pagination for results tables
  - Use data sampling for previews
  - Lazy loading for visualizations
  - Progress indicators for long operations
  - Backend caching strategy

**3. Visualization Rendering Issues**
- **Impact:** Charts fail to display, poor performance
- **Probability:** MEDIUM
- **Mitigation:**
  - Use Plotly for primary visualizations (well-supported in Streamlit)
  - Fallback to static images for complex charts
  - Implement chart complexity limits
  - Test with diverse dataset shapes

### Medium Risks

**4. State Management Complexity**
- **Impact:** Lost configuration, inconsistent UI
- **Probability:** MEDIUM
- **Mitigation:**
  - Centralized state management patterns
  - Comprehensive state initialization
  - State persistence to backend
  - Clear state reset mechanisms

**5. API Error Handling Gaps**
- **Impact:** Cryptic errors confuse users
- **Probability:** LOW-MEDIUM
- **Mitigation:**
  - Comprehensive error handling layer
  - User-friendly error messages
  - Retry mechanisms for transient failures
  - Error logging for debugging

**6. Mobile/Tablet Responsiveness**
- **Impact:** Poor experience on non-desktop devices
- **Probability:** LOW (prototype phase)
- **Mitigation:**
  - Desktop-first design (primary use case)
  - Basic responsive CSS for tablet
  - Document mobile limitations
  - Plan for responsive redesign in production phase

### Low Risks

**7. Browser Compatibility Issues**
- **Impact:** Features broken in specific browsers
- **Probability:** LOW
- **Mitigation:**
  - Target modern browsers (evergreen)
  - Test in Chrome, Firefox, Edge
  - Document minimum browser versions
  - Graceful degradation for unsupported features

---

## Success Criteria

### Functional Requirements
- ✅ User can upload CSV/Excel/Parquet datasets < 100MB
- ✅ Dataset profile displays after upload with column types and statistics
- ✅ User can select/deselect columns (default all selected)
- ✅ User can add multiple filters (numeric ranges, categorical values)
- ✅ Configuration preview updates within 2 seconds
- ✅ User can toggle between three analysis modes
- ✅ Mode-specific parameters display correctly
- ✅ User can save configuration as named template
- ✅ User can load and apply saved templates
- ✅ User can execute analysis with "Run Analysis" button
- ✅ Progress indicator displays during analysis
- ✅ Correlation results display with table, heatmap, and network graph
- ✅ Multivariate results display with coefficients and diagnostics
- ✅ Auto-triage results display with rankings, PCA, and change-points
- ✅ Confidence flags display on all results
- ✅ User can export results as JSON
- ✅ User can export reduced dataset (top-N variables)
- ✅ User can view audit trail for dataset
- ✅ Error messages are clear and actionable
- ✅ Help tooltips available for all major features

### Non-Functional Requirements
- ✅ Page loads in < 3 seconds
- ✅ Visualizations render in < 10 seconds
- ✅ Application remains responsive with 50k row datasets
- ✅ State persists across page navigation
- ✅ All interactions provide immediate feedback
- ✅ Layout remains usable on screens ≥ 1280px width
- ✅ No critical errors in browser console
- ✅ Code follows PEP 8 style guidelines
- ✅ Components have docstrings
- ✅ README documentation complete

### Quality Metrics
- **Test Coverage:** ≥ 70% for utility functions and API client
- **Performance:** All target benchmarks met
- **Bugs:** Zero critical bugs, < 5 minor bugs at launch
- **Documentation:** User guide and developer guide complete
- **Accessibility:** Basic keyboard navigation support

---

## Appendix A: Technology Stack

### Frontend Dependencies
```toml
# requirements-frontend.txt
streamlit==1.29.0
plotly==5.18.0
pandas==2.1.4
numpy==1.26.2
requests==2.31.0
Pillow==10.1.0
```

### Development Dependencies
```toml
# requirements-frontend-dev.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
black==23.12.1
ruff==0.1.8
mypy==1.7.1
```

---

## Appendix B: File Structure

```
frontend/streamlit_app/
├── app.py                          # Main entry point (180 lines)
├── config.py                       # Configuration (50 lines)
├── pages/
│   ├── 1_📊_Dataset_Upload.py     # Upload page (200 lines)
│   ├── 2_⚙️_Configuration.py      # Config page (350 lines)
│   ├── 3_🔬_Analysis.py            # Analysis page (400 lines)
│   └── 4_📋_Templates.py           # Template page (150 lines)
├── components/
│   ├── __init__.py                 # Component exports (30 lines)
│   ├── upload.py                   # Upload widget (120 lines)
│   ├── column_selector.py          # Column selector (200 lines)
│   ├── filter_panel.py             # Filter builder (280 lines)
│   ├── mode_selector.py            # Mode toggle (150 lines)
│   ├── correlation_view.py         # Correlation display (350 lines)
│   ├── multivariate_view.py        # Multivariate display (300 lines)
│   ├── auto_triage_view.py         # Auto-triage display (400 lines)
│   ├── visualizations.py           # Chart functions (500 lines)
│   ├── confidence_flags.py         # Flag badges (80 lines)
│   ├── audit_viewer.py             # Audit display (150 lines)
│   └── export_controls.py          # Export buttons (100 lines)
├── utils/
│   ├── __init__.py                 # Utility exports (20 lines)
│   ├── api_client.py               # API wrapper (600 lines)
│   ├── session_state.py            # State helpers (100 lines)
│   ├── formatters.py               # Data formatters (150 lines)
│   └── validators.py               # Input validation (120 lines)
├── assets/
│   ├── styles.css                  # Custom CSS (200 lines)
│   └── logo.png                    # App logo
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py          # API tests (300 lines)
│   ├── test_formatters.py          # Formatter tests (100 lines)
│   └── test_validators.py          # Validation tests (80 lines)
├── README.md                       # User documentation
├── requirements.txt                # Dependencies
└── requirements-dev.txt            # Dev dependencies

Estimated Total: ~5,500 lines of Python code
```

---

## Appendix C: Next Steps After Milestone 9

### Immediate Follow-up (Milestone 10)
1. **Backend Analysis Endpoint** (if not done in M9)
2. **AI Summarization Integration** (connect real LLM)
3. **Export Enhancements** (PDF reports, Excel with formatting)
4. **Advanced Visualizations** (3D plots, animated transitions)

### Medium-Term (Milestones 11-12)
5. **Performance Optimizations** (caching, lazy loading)
6. **User Authentication** (login, sessions)
7. **Dataset Management** (versioning, archiving)
8. **Batch Analysis** (multiple datasets, scheduled runs)

### Long-Term (Milestones 13+)
9. **Production Frontend** (React/Dash migration)
10. **Advanced Analytics** (time series, forecasting)
11. **Collaboration Features** (sharing, comments)
12. **Enterprise Integration** (LDAP, SSO, data connectors)

---

## Document Control

**Author:** AI Development Assistant  
**Reviewed By:** [Pending Team Review]  
**Approved By:** [Pending]  
**Last Updated:** 2025-01-14  
**Version:** 1.0  
**Status:** Draft - Awaiting Feedback

### Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-14 | AI Assistant | Initial detailed plan created |

### Review Checklist
- [ ] Architecture reviewed by tech lead
- [ ] Design mockups approved by stakeholders
- [ ] API integration strategy validated
- [ ] Timeline and effort estimates reviewed
- [ ] Risk assessment complete
- [ ] Success criteria agreed upon
- [ ] Testing strategy approved
- [ ] Color scheme selected
- [ ] Component specifications finalized
- [ ] Ready to begin implementation

---

**END OF DOCUMENT**
