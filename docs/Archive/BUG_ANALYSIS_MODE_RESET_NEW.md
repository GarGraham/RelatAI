# Bug Report: Analysis Mode Appears to Reset to Correlation

**Date**: 2025-10-22  
**Severity**: HIGH  
**Status**: Root Cause Reassessed  

---

## Bug Description

When a user believes they have switched the Analysis Mode to **Auto-Triage** on the Configuration page and then navigates to the Analysis page, the banner still reads `Analysis Mode: correlation`. The expectation is that the Auto-Triage selection should persist through to the analysis run.

### Reproduction (User Workflow)
1. Open **Configuration** (`frontend/streamlit_app/pages/2_⚙️_Configuration.py`).
2. Click the **Auto-Triage** tab within "Choose Analysis Mode".
3. **Do not press** the "Select Auto-Triage Mode" button (the user assumes tab activation is sufficient).
4. Click **Apply Configuration**.
5. Navigate to the **Analysis** page.
6. Observe `Analysis Mode: correlation`.

The user’s screenshot confirms the Auto-Triage tab was active, yet no success banner (“✅ Auto-Triage mode active”) was displayed—meaning the underlying state never changed.

---

## Impact
- **Functional**: Auto-Triage analysis never runs because the configuration still points to the default `correlation` mode.
- **User Experience**: UI provides misleading feedback—tab activation changes layout but not the saved configuration, so users believe their choice was honored.
- **Data/Decision Risk**: Analysts unknowingly operate with the wrong statistical workflow.

---

## Root Cause

### Summary
`render_mode_selector()` stores the chosen analysis mode exclusively through the "Select … Mode" buttons. Clicking a tab *only* reveals descriptive content—it does **not** mutate `st.session_state.selected_mode`. Therefore, when Apply is clicked without pressing the button, `_apply_configuration()` sends the previous mode (`correlation`) to the backend, which persists it. The Analysis page then correctly reports `correlation`.

### Detailed Trace
- **File**: `frontend/streamlit_app/components/mode_selector.py`
- **Critical snippet**:
  ```python
  with tab3:
      if st.button("Select Auto-Triage Mode", ...):
          st.session_state.selected_mode = "auto_triage"
          st.rerun()
  ```
- Tab interaction alone does not touch `selected_mode`.
- `_apply_configuration()` passes `analysis_mode=new_mode` where `new_mode` is the return value of `render_mode_selector()`—the unchanged previous mode.
- Backend persists correlation and returns that value; `get_analysis_mode()` reads it and the Analysis page displays `correlation`.

### Discarded Hypothesis
The earlier investigation blamed session-state reinitialization and proposed always syncing `selected_mode` with the stored configuration. This was incorrect: the actual failure is UX-related. Implementing that proposal would in fact prevent any mode change because each rerun would immediately revert the user’s selection.

---

## Recommended Fix

### Option A (Preferred): Single Control Selection
- Replace tabs + buttons with a single explicit control (`st.radio` or `st.segmented_control`) that simultaneously switches content and updates `selected_mode`.
- Display mode-specific descriptions/parameters conditionally below the control.

### Option B: Auto-select on Tab Activation
- Keep tab layout for visual grouping but set `st.session_state.selected_mode` as soon as a tab renders, eliminating the button entirely.
- Example:
  ```python
  with tab3:
      st.session_state.selected_mode = "auto_triage"
      ...
  ```
- Remove the “Select … Mode” buttons to avoid duplicate interactions.

### Additional Safeguards
- Show a confirmation banner whenever the selection changes.
- Optionally disable the Apply button until a mode selection differs from the persisted configuration.
- Update inline help to match the new interaction pattern.

---

## Next Steps
1. Implement Option A or B in `mode_selector.py`.
2. Remove now-redundant confirmation buttons.
3. Regression-test all three modes to confirm the payload carries the correct `analysis_mode`.
4. Update documentation/onboarding screenshots after UI change.

---

**Investigated By**: GitHub Copilot  
**Reassessment Date**: 2025-10-22  
**Status**: Awaiting UX update to mode selector
