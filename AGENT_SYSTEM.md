# AGENT_SYSTEM.md — System Glue

## Role
Defines how the system operates: routing, chaining, memory, proof-of-life, dependencies, and conflict resolution.

---

## Skill Routing Rules
- If a task matches a skill, use it
- If multiple match, choose the most specific
- If ambiguous, ask a short clarifying question
- If none match, follow `agents.md` Guidelines

---

## Phases (Stable, Future-Proof)
All work falls into one or more phases:

### 1) Understand
- Learn what exists
- Map flows
- Identify constraints

### 2) Change
- Add, modify, or restructure behavior

### 3) Validate
- Check correctness
- Reduce risk
- Add Proof of Life

---

## Default Phase → Skill Mapping (Extensible)
- Understand → Discovery
- Change → Feature Development, Refactoring, Debugging
- Validate → Code Review, Testing

New skills should declare their primary phase.

---

## Example Skill Chains (Non-Exclusive)
- Unknown code → safe change:
  - Discovery → Feature Development → Code Review
- Big cleanup:
  - Discovery → Refactoring → Code Review
- Something broke:
  - Debugging → Feature Development → Code Review
- Repo onboarding:
  - Discovery → Journal update
- Quality assurance:
  - Code Review → Testing

---

## Change Size Heuristic
- Small: 1–3 files → direct
- Medium: multiple areas → short plan
- Large: wide blast radius → phased

---

## Memory Rules
- **SCRATCHPAD.md**: Use for active tasks; must include "Rejected Approaches" to prevent repetitive failure loops.
- **JOURNAL.md**: Append one line after every "Change" phase completion.
- **Long-Term Memory Promotion**: Upon completion of a Medium/Large task, the agent MUST review the `Rejected Approaches` and `Open Questions` in the `SCRATCHPAD.md`. Any persistent known hazards or non-obvious architecture choices must be moved to the **Known Hazards** or **Decision Log** sections of the `REPO_PROFILE.md` (or their respective docs) before the scratchpad is cleared.

---

## Proof of Life Rule
Every meaningful change must include a concrete way to verify it works:
- Test
- URL
- curl
- CLI output
- UI interaction

---

## Dependency Nutrition Label Rule
When proposing a dependency, include:
- What it does
- Approximate size / cost (rough is fine)
- Why it’s worth it
- Lightweight alternative (if applicable)

---

## Conflict Resolution
- `agents.md` > `AGENT_SYSTEM.md` > `SKILL.md` > suggestions
- More specific beats more general
- When intent is unclear, propose two distinct paths with pros/cons, then stop and ask.

---

## Skill Structure
Each skill file should:
- Open with a back-reference: `> See also: AGENT_SYSTEM.md`
- Declare its primary phase
- Define inputs, workflow, and outputs
- Be self-contained (copy-pasteable to an agent)

---

## Commit Hygiene
All commits must follow the conventional prefix standard to support future "Product" status:
- `feat:` New features or logic.
- `fix:` Bug fixes or error handling.
- `refactor:` Code changes that neither fix a bug nor add a feature.
- `docs:` Documentation only.
- `test:` Adding or correcting tests.
