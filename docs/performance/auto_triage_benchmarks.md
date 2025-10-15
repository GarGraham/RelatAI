# Auto-Triage Benchmark Baselines

The following metrics were captured using `pytest --benchmark-only` on a
reference workstation (Apple M2 Pro, 32GB RAM) with a synthetic dataset of
1,000 rows and three numeric features.

| Routine                         | Mean (ms) | Std Dev (ms) |
|---------------------------------|-----------|--------------|
| `_prepare_numeric_matrix`       | 3.21      | 0.41         |
| `_perform_clustering`           | 8.57      | 0.92         |
| `_detect_change_points`         | 12.44     | 1.38         |
| `run_auto_triage` end-to-end    | 46.72     | 3.95         |

> Benchmarks captured on 2025-03-18. Re-run benchmarks after material changes
> to the auto-triage pipeline and update this document with the new baseline.
