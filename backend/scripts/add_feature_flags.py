"""Utility script to backfill feature flag defaults into existing .env files."""

from __future__ import annotations

import argparse
from pathlib import Path

FEATURE_FLAGS = {
    "AUTO_TRIAGE_EXPLAINABILITY": "false",
    "VISUALIZATION_PRESET_PATH": "infrastructure/config/visualization.yml",
}


def ensure_feature_flags(env_path: Path) -> None:
    if not env_path.exists():
        return

    existing = env_path.read_text(encoding="utf-8").splitlines()
    present_keys = {line.split("=", 1)[0].strip() for line in existing if "=" in line}
    additions = [
        f"{key}={value}" for key, value in FEATURE_FLAGS.items() if key not in present_keys
    ]
    if not additions:
        return

    env_path.write_text("\n".join(existing + ["", *additions]) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill feature flags into .env files")
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path(".env"),
        help="Path to the .env file (default: repository root .env)",
    )
    args = parser.parse_args()
    ensure_feature_flags(args.path)

if __name__ == "__main__":
    main()
