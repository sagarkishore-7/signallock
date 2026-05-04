# SignalLock Experiments

## Purpose

SignalLock now supports a lightweight experiment workflow for comparing policy profiles over synthetic profile-password scenarios and saving each run as a reproducible artifact bundle.

The goal is not large-scale benchmarking yet. The goal is to make iterative research work traceable and easy to review.

## Current Workflow

1. Generate a reproducible batch of synthetic public profiles.
2. Generate safe synthetic password scenarios for each profile.
3. Evaluate one or more policy profiles over the same scenario set.
4. Save the run to a timestamped artifact directory.
5. Inspect the JSON summaries and markdown comparison table.

## CLI Example

```bash
PYTHONPATH=src python3 -m signallock evaluate-policies \
  --count 5 \
  --seed 1 \
  --policy-profiles balanced strict usability \
  --include-table \
  --save-run \
  --output-dir artifacts/evaluations \
  --pretty
```

## Artifact Layout

Saved runs are written under:

`artifacts/evaluations/<timestamp>/`

Each run currently contains:

- `report.json`
- `summaries.json`
- `comparison_table.md`
- `records.json` when `--include-records` is used

## File Semantics

### `report.json`

Single-file bundle intended for later analysis or sharing inside the research workflow.

Contains:

- generation timestamp
- run id
- CLI metadata such as seed and selected policy profiles
- aggregate summaries
- optional per-scenario records
- embedded markdown comparison table

### `summaries.json`

Focused aggregate output for quick parsing and scriptable comparisons.

### `comparison_table.md`

Human-readable markdown table for notes, progress updates, or thesis draft figures.

### `records.json`

Optional per-scenario output for more detailed debugging or later statistical analysis.

## Reproducibility Notes

- Use `--seed` for stable synthetic profile generation.
- Use `--policy-file` when testing alternate thresholds.
- Treat the generated artifacts as local research outputs; the `artifacts/` directory is intentionally gitignored.

## Current Limitations

- The scenarios are still heuristic and synthetic.
- The markdown table is summary-focused, not publication-grade plotting.
- No calibration or confidence intervals are produced yet.
- The artifact format is stable enough for local iteration, but may evolve as the research design matures.
