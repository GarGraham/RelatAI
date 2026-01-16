---
name: environment-automation
description: Use this to set up dev environments, build scripts, CI/CD pipelines, or fix "works on my machine" issues.
---
# Skill: Environment & Automation

> See also: `AGENT_SYSTEM.md`

## Phase
- Change / Validate

## Purpose
- Ensure environment parity and automate repetitive tasks (build, deploy, lint).

## Use When
- "Make this work on another machine"
- "Add a Dockerfile"
- "Set up GitHub Actions"
- "Automate the build process"

## Workflow
- **Audit:** Check for hardcoded local paths, environment variables, or missing dependencies.
- **Standardize:** Use tools like `Docker`, `asdf`, or `devcontainer` to lock versions.
- **Automate:** Wrap complex setup steps into a single `scripts/setup` or `make` command.
- **Verify:** Attempt to run the "Proof of Life" in a clean environment (e.g., a temporary container).

## Output
- **Environment Changes:** List of new configs/scripts.
- **Setup Steps:** The "One Command" to get started.
- **Proof of Life:** Verification that the build/environment is stable.
