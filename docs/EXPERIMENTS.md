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
6. Aggregate multiple saved runs into cross-run markdown and CSV outputs.
7. Generate lightweight SVG figures and aggregate policy tables.

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

Cross-run analysis bundles can also be written under:

`artifacts/analysis/<timestamp>/`

These bundles currently contain:

- `analysis.json`
- `comparison_table.md`
- `policy_matrix.csv`

Figure bundles can also be written under:

`artifacts/figures/<timestamp>/`

These bundles currently contain:

- `figure_summary.json`
- `policy_aggregates.csv`
- `policy_summary_table.md`
- `policy_score_summary.svg`
- `policy_action_summary.svg`

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

### `analysis.json`

Cross-run analysis bundle containing:

- overall run metadata
- flattened per-run policy rows
- embedded comparison table markdown

### `policy_matrix.csv`

Flat export intended for plotting, spreadsheet analysis, or later statistical work.

### `figure_summary.json`

Aggregate policy metrics and figure metadata for one saved figure-generation run.

### `policy_score_summary.svg`

Grouped bar chart comparing mean combined, exposure, and password scores by policy.

### `policy_action_summary.svg`

Stacked distribution chart showing how dominant recommendation actions vary by policy across runs.

## Cross-Run Analysis

Use the saved run directories as input to:

```bash
PYTHONPATH=src python3 -m signallock analyze-runs \
  --input-dir artifacts/evaluations \
  --include-table \
  --save-analysis \
  --pretty
```

Optional flags:

- `--policy-profiles` to focus on one or more policy profiles
- `--include-rows` to emit flattened per-run rows in JSON
- `--output-dir` to control where analysis bundles are written

## Figure Generation

Generate a lightweight figure bundle directly from saved evaluation runs:

```bash
PYTHONPATH=src python3 -m signallock generate-figures \
  --input-dir artifacts/evaluations \
  --include-aggregates \
  --include-table \
  --save-figures \
  --pretty
```

Optional flags:

- `--policy-profiles` to focus on one or more policy profiles
- `--output-dir` to control where figure bundles are written
- `--include-aggregates` to include aggregate metrics in JSON
- `--include-table` to include the markdown summary table in JSON

## Reproducibility Notes

- Use `--seed` for stable synthetic profile generation.
- Use `--policy-file` when testing alternate thresholds.
- Treat the generated artifacts as local research outputs; the `artifacts/` directory is intentionally gitignored.

## Current Limitations

- The scenarios are still heuristic and synthetic.
- The markdown table is summary-focused, not publication-grade plotting.
- The CSV is intentionally flat and minimal rather than analysis-framework-specific.
- The SVG figures are lightweight and dependency-free, but not a replacement for final publication plotting.
- No calibration or confidence intervals are produced yet.
- The artifact format is stable enough for local iteration, but may evolve as the research design matures.
