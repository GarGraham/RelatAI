---
name: code-review
description: Provide a practical review of code changes, focusing on bugs, risk, security, and maintainability.
---
# Skill: Code Review

> See also: `AGENT_SYSTEM.md`

## Phase
- Validate

## Purpose
- Provide a practical review: bugs, risk, security basics, and “is this worth it?”

## Use When
- “Review this”
- “Is this approach okay?”
- “Find issues”
- “Suggest improvements”

## Inputs to Request (only if needed)
- Diff/PR/files
- Intended behavior change
- Any constraints (timebox, no deps, etc.)

## Rubric (priority order)
- Bugs/correctness
- Security/Known Hazards
- Verification/Proof of Life
- Maintainability
- Style (last)

## Severity
- **BLOCKER**: likely bug/security issue/breakage
- **SUGGESTION**: better approach, reduces risk
- **NIT**: small style/naming notes (keep minimal)

## Output
- **Summary**
- **Findings** (grouped by severity)
- **Suggested verification**
- **Merge confidence** (0–100%) + 1-line why
