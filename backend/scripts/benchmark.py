"""CLI utility for benchmarking analysis pipelines."""

from __future__ import annotations

import argparse
from pathlib import Path
import time

import pandas as pd

from relat_ai.services.analysis import compute_pairwise_correlations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark RelatAI analysis throughput")
    parser.add_argument("dataset", type=Path, help="Path to dataset file (CSV or Parquet)")
    parser.add_argument(
        "--method",
        choices=["pearson", "spearman", "kendall"],
        default="pearson",
        help="Correlation method to benchmark",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = pd.read_csv(args.dataset)
    start = time.perf_counter()
    result = compute_pairwise_correlations(frame, frame.columns, method=args.method)
    duration = time.perf_counter() - start
    print(f"Computed {len(list(result.correlations or []))} correlations in {duration:.2f}s")


if __name__ == "__main__":
    main()
