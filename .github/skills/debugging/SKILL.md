---
name: debugging
description: Interpret errors and propose minimal fixes for crashes, failing tests, or broken builds.
---
# Skill: Debugging

> See also: `AGENT_SYSTEM.md`

## Phase
- Change (often preceded by Understand)

## Purpose
- Interpret errors before proposing fixes; avoid shotgun debugging.

## Use When
- “This error happened…”
- “App crashes”
- “Tests failing”
- “Build broke”
- “Stack trace help”

## Inputs to Request (only if needed)
- Full error output (or the relevant part)
- What command/action triggered it
- Expected behavior vs actual

## Workflow
- Extract facts first:
  - error type/class
  - file + line number(s)
  - failing command
- Hypothesize cause:
  - 1–3 likely causes, ranked
  - If stuck after 2 hypotheses, switch to **Discovery** skill to trace the code flow
- Propose fix:
  - minimal change first
  - call out tradeoffs
- Proof of Life:
  - exact command to re-run
  - what output indicates success

## Output
- **Error summary** (facts)
- **Likely cause(s)** (ranked bullets)
- **Proposed fix** (bullets)
- **Proof of Life**
