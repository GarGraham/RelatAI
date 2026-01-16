---
name: discovery
description: Map unfamiliar code, trace data flows, and identify entry points without changing behavior.
---
# Skill: Discovery

> See also: `AGENT_SYSTEM.md`

## Phase
- Understand

## Purpose
- Map unfamiliar or confusing code without changing it.

## Use When
- “How does X work?”
- “Where is Y handled?”
- “Trace the data flow”
- “What calls this?”

## Inputs to Request (only if needed)
- What is the user trying to understand (X/Y/Z)?
- Any suspected area (file, module, feature name)?
- Any constraints (timebox, depth)?

## Workflow
- Search the codebase (grep/ripgrep/find) before guessing
- Identify entry points:
  - routes/controllers/handlers
  - CLI entry
  - UI entry component
- Trace flow:
  - entry → processing → storage/output
- Identify side effects:
  - DB writes
  - external API calls
  - filesystem
  - global state
- Note “gotchas”:
  - duplicated logic
  - dead/legacy paths
  - confusing naming

## Output
- **Map**: bullet list of key files + 1-line role each
- **Flow**: 2–3 sentence summary
- **Gotchas**: bullets

## Guardrails
- Don’t propose changes unless asked
- Don’t speculate; label unknowns clearly
