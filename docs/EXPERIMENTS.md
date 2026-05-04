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
7. Compare baseline and candidate policies across saved runs.
8. Generate lightweight SVG figures and aggregate policy tables.
9. Execute named presets that orchestrate the entire workflow automatically.
10. Summarize executed preset bundles into thesis-friendly markdown and CSV outputs.

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

Comparison bundles can also be written under:

`artifacts/comparisons/<timestamp>/`

These bundles currently contain:

- `comparison_summary.json`
- `comparison_table.md`
- `run_deltas.csv`
- `comparison_deltas.svg`

Preset bundles can also be written under:

`artifacts/presets/<timestamp>-<preset>/`

These bundles currently contain:

- `preset_manifest.json`
- `evaluations/`
- `analysis/`
- `comparisons/`
- `figures/`

Preset-results summary bundles can also be written under:

`artifacts/results/<timestamp>/`

These bundles currently contain:

- `preset_results_summary.json`
- `preset_runs.csv`
- `preset_policy_summaries.csv`
- `preset_comparison_summaries.csv`
- `preset_summary_table.md`
- `preset_policy_summary_table.md`
- `preset_comparison_summary_table.md` when comparisons exist

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

### `comparison_summary.json`

Pairwise baseline-versus-candidate comparison metadata and aggregate delta summaries.

### `run_deltas.csv`

Per-run policy deltas for candidate-versus-baseline comparisons.

### `comparison_deltas.svg`

Mean delta chart showing how candidate profiles differ from the baseline across key scores.

### `preset_manifest.json`

Top-level manifest for one preset execution, including the generated evaluation, analysis, comparison, and figure artifact paths.

### `preset_results_summary.json`

Aggregate view across one or more executed preset bundles, including:

- preset-run metadata
- per-policy preset summaries
- per-candidate preset comparison summaries
- embedded markdown tables for quick reporting

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

## Policy Comparison

Compare one baseline profile against one or more candidate profiles:

```bash
PYTHONPATH=src python3 -m signallock compare-policies \
  --input-dir artifacts/evaluations \
  --baseline-profile balanced \
  --candidate-profiles strict usability \
  --include-run-deltas \
  --include-table \
  --save-comparison \
  --pretty
```

Optional flags:

- `--candidate-profiles` to compare a subset rather than all non-baseline profiles
- `--include-run-deltas` to include per-run deltas in JSON
- `--output-dir` to control where comparison bundles are written

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

## Preset Execution

List the available presets:

```bash
PYTHONPATH=src python3 -m signallock list-experiment-presets --pretty
```

Run a preset end to end:

```bash
PYTHONPATH=src python3 -m signallock run-preset \
  --preset baseline_matrix \
  --pretty
```

Use a custom preset file:

```bash
PYTHONPATH=src python3 -m signallock run-preset \
  --preset mini_suite \
  --preset-file /path/to/presets.json \
  --output-dir /tmp/signallock-preset-runs \
  --pretty
```

## Preset Summaries

Summarize previously executed preset bundles:

```bash
PYTHONPATH=src python3 -m signallock summarize-presets \
  --input-dir artifacts/presets \
  --include-runs \
  --include-policy-summaries \
  --include-comparison-summaries \
  --include-tables \
  --save-summary \
  --pretty
```

Optional flags:

- `--preset-names` to focus on a subset of named presets
- `--output-dir` to control where summary bundles are written
- `--include-runs` to include flattened preset-run records in JSON
- `--include-policy-summaries` to include per-policy preset summaries in JSON
- `--include-comparison-summaries` to include comparison summaries in JSON

## Reproducibility Notes

- Use `--seed` for stable synthetic profile generation.
- Use `--policy-file` when testing alternate thresholds.
- Treat the generated artifacts as local research outputs; the `artifacts/` directory is intentionally gitignored.

## Current Limitations

- The scenarios are still heuristic and synthetic.
- The markdown table is summary-focused, not publication-grade plotting.
- The CSV is intentionally flat and minimal rather than analysis-framework-specific.
- The SVG figures are lightweight and dependency-free, but not a replacement for final publication plotting.
- Pairwise comparisons are based on saved synthetic run summaries, so they are useful for ablation-style iteration rather than definitive deployment claims.
- Preset orchestration improves reproducibility, but it still operates on heuristic synthetic pipelines rather than calibrated study data.
- Preset summaries are designed for traceability and draft reporting, not final statistical claims.
- No calibration or confidence intervals are produced yet.
- The artifact format is stable enough for local iteration, but may evolve as the research design matures.
