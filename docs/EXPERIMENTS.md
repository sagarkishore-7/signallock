# SignalLock Experiments

## Purpose

SignalLock now supports a lightweight experiment workflow for comparing policy profiles over synthetic profile-password scenarios and saving each run as a reproducible artifact bundle.

The goal is not large-scale benchmarking yet. The goal is to make iterative research work traceable and easy to review.

The current evaluation layer also attaches proxy calibration targets to each synthetic scenario so we can estimate:

- whether a policy under-hardens high-risk synthetic passwords,
- whether a policy over-hardens low-risk synthetic passwords,
- how often recommendations stay within an expected severity range,
- and how strict each policy behaves across the same scenario mix.

## Current Workflow

1. Generate a reproducible batch of synthetic public profiles.
2. Generate safe synthetic password scenarios for each profile.
3. Evaluate one or more policy profiles over the same scenario set.
4. Save the run to a timestamped artifact directory.
5. Inspect the JSON summaries and markdown comparison table.
6. Inspect the proxy calibration summaries and markdown calibration table.
7. Aggregate multiple saved runs into cross-run markdown and CSV outputs.
8. Compare baseline and candidate policies across saved runs.
9. Generate lightweight SVG figures and aggregate policy tables.
10. Execute named presets that orchestrate the entire workflow automatically.
11. Summarize executed preset bundles into thesis-friendly markdown and CSV outputs.
12. Aggregate preset summaries into paper-style cross-preset result tables.
13. Run threshold-sensitivity sweeps to study calibration changes without editing policy files.
14. Aggregate saved threshold sweeps into cross-run sensitivity summaries.
15. Generate threshold-sweep SVG figures for thesis-ready review.

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
- `calibration_summaries.json`
- `calibration_table.md`
- `records.json` when `--include-records` is used

Cross-run analysis bundles can also be written under:

`artifacts/analysis/<timestamp>/`

These bundles currently contain:

- `analysis.json`
- `comparison_table.md`
- `policy_matrix.csv`
- `calibration_table.md`
- `calibration_matrix.csv`

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
- `preset_calibration_summaries.csv`
- `preset_comparison_summaries.csv`
- `preset_summary_table.md`
- `preset_policy_summary_table.md`
- `preset_calibration_summary_table.md`
- `preset_comparison_summary_table.md` when comparisons exist

Preset aggregate bundles can also be written under:

`artifacts/preset_aggregates/<timestamp>/`

These bundles currently contain:

- `preset_aggregate_summary.json`
- `preset_policy_aggregates.csv`
- `preset_calibration_aggregates.csv`
- `preset_comparison_aggregates.csv`
- `cross_preset_policy_aggregates.csv`
- `cross_preset_calibration_aggregates.csv`
- `cross_preset_comparison_aggregates.csv`
- `preset_policy_aggregate_table.md`
- `preset_calibration_aggregate_table.md`
- `preset_comparison_aggregate_table.md`
- `cross_preset_policy_aggregate_table.md`
- `cross_preset_calibration_aggregate_table.md`
- `cross_preset_comparison_aggregate_table.md` when comparisons exist

Threshold-sweep bundles can also be written under:

`artifacts/threshold_sweeps/<timestamp>/`

These bundles currently contain:

- `threshold_sweep_summary.json`
- `threshold_sweep_records.csv`
- `threshold_sweep_table.md`

Threshold-sweep analysis bundles can also be written under:

`artifacts/threshold_sweep_analysis/<timestamp>/`

These bundles currently contain:

- `threshold_sweep_analysis.json`
- `threshold_sweep_rows.csv`
- `threshold_sweep_run_table.md`
- `threshold_sweep_aggregates.csv`
- `threshold_sweep_aggregate_table.md`

Threshold-sweep figure bundles can also be written under:

`artifacts/threshold_sweep_figures/<timestamp>/`

These bundles currently contain:

- `threshold_sweep_figure_summary.json`
- `threshold_sweep_aggregates.csv`
- `threshold_sweep_summary_table.md`
- `threshold_sweep_within_range.svg`
- `threshold_sweep_false_positive.svg`
- `threshold_sweep_action_change.svg`

## File Semantics

### `report.json`

Single-file bundle intended for later analysis or sharing inside the research workflow.

Contains:

- generation timestamp
- run id
- CLI metadata such as seed and selected policy profiles
- aggregate summaries
- proxy calibration summaries
- optional per-scenario records
- embedded markdown comparison table
- embedded markdown calibration table

### `summaries.json`

Focused aggregate output for quick parsing and scriptable comparisons.

### `comparison_table.md`

Human-readable markdown table for notes, progress updates, or thesis draft figures.

### `calibration_table.md`

Human-readable markdown table summarizing proxy calibration behavior per policy.

Columns currently emphasize:

- within-range agreement,
- under-hardening rate,
- over-hardening rate,
- true-positive proxy rate on higher-risk scenarios,
- false-positive proxy rate on low-risk scenarios,
- and action-severity gap.

### `records.json`

Optional per-scenario output for more detailed debugging or later statistical analysis.

The current record payload now includes proxy expectations for each synthetic scenario, such as:

- expected risk band,
- expected action floor,
- expected action ceiling,
- whether the chosen action fell within that range,
- and whether the policy under- or over-hardened the scenario.

### `analysis.json`

Cross-run analysis bundle containing:

- overall run metadata
- flattened per-run policy rows
- flattened per-run calibration rows
- embedded comparison table markdown
- embedded calibration table markdown

### `policy_matrix.csv`

Flat export intended for plotting, spreadsheet analysis, or later statistical work.

### `calibration_matrix.csv`

Flat export of cross-run calibration summaries intended for threshold review, false-positive proxy analysis, and later plotting.

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
- per-policy preset calibration summaries
- per-candidate preset comparison summaries
- embedded markdown tables for quick reporting

### `preset_aggregate_summary.json`

Higher-level aggregate view across executed preset summaries, including:

- within-preset policy aggregates
- within-preset calibration aggregates
- within-preset baseline-versus-candidate aggregates
- cross-preset policy aggregates
- cross-preset calibration aggregates
- cross-preset comparison aggregates
- embedded markdown tables that are easier to lift into a thesis draft

### `threshold_sweep_summary.json`

Threshold-sensitivity experiment output including:

- the base policy profile,
- the applied threshold offsets,
- one record per threshold variant,
- score summaries per variant,
- calibration summaries per variant,
- per-variant deltas relative to the nearest-to-zero reference threshold profile,
- and a markdown table for quick inspection.

### `threshold_sweep_analysis.json`

Cross-run threshold-sweep analysis output including:

- analysis metadata across saved sweep bundles,
- flattened per-run threshold-sweep rows,
- aggregate rows grouped by base profile and applied threshold offset,
- a markdown run table,
- and a markdown aggregate table for sensitivity review.

### `threshold_sweep_figure_summary.json`

Threshold-sweep figure bundle metadata including:

- analysis metadata for the selected sweep runs,
- the aggregate rows used to generate the figures,
- a markdown summary table,
- and saved references to the generated SVG charts.

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

The `--include-rows` output now includes both score rows and calibration rows.

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

The preset-summary JSON now also includes calibration summaries whenever `--include-policy-summaries` is enabled.

## Preset Aggregates

Build paper-style aggregate tables from executed preset bundles:

```bash
PYTHONPATH=src python3 -m signallock aggregate-presets \
  --input-dir artifacts/presets \
  --include-tables \
  --save-aggregates \
  --pretty
```

Optional flags:

- `--preset-names` to focus on selected preset families
- `--output-dir` to control where aggregate bundles are written
- `--include-tables` to embed the markdown tables directly in JSON

## Threshold Sweeps

Run a threshold-sensitivity study directly from the CLI:

```bash
PYTHONPATH=src python3 -m signallock sweep-thresholds \
  --base-profile balanced \
  --count 5 \
  --seed 1 \
  --threshold-offsets -12 -8 -4 0 4 8 12 \
  --include-table \
  --save-sweep \
  --pretty
```

This command applies additive shifts to the selected profile's `warn`, `step_up`, and `enforce_mfa` score thresholds while preserving the rest of the profile configuration.

Useful outputs:

- how stricter or looser score thresholds change proxy false positives,
- how they affect under-hardening and within-range agreement,
- how far each variant drifts from the reference threshold profile,
- and where the dominant action shifts from `ALLOW` to `WARN`, `STEP_UP_AUTHENTICATION`, or `REQUIRE_STRONGER_PASSWORD`.

Aggregate saved threshold sweeps across repeated runs:

```bash
PYTHONPATH=src python3 -m signallock analyze-threshold-sweeps \
  --input-dir artifacts/threshold_sweeps \
  --include-rows \
  --include-aggregates \
  --include-tables \
  --save-analysis \
  --pretty
```

This command is useful for:

- comparing the same offset across multiple seeds or organizations,
- seeing whether reference-relative deltas are stable across runs,
- and deciding which threshold ranges are worth promoting into reusable policy profiles.

Generate threshold-sweep figures directly from saved sweep bundles:

```bash
PYTHONPATH=src python3 -m signallock generate-threshold-sweep-figures \
  --input-dir artifacts/threshold_sweeps \
  --include-aggregates \
  --include-table \
  --save-figures \
  --pretty
```

This command is useful for:

- turning sweep aggregates into review-friendly SVGs,
- comparing within-range, false-positive, and action-change behavior by offset,
- and dropping threshold-tuning visuals into notes or draft papers.

## Reproducibility Notes

- Use `--seed` for stable synthetic profile generation.
- Use `--policy-file` when testing alternate thresholds.
- Treat the generated artifacts as local research outputs; the `artifacts/` directory is intentionally gitignored.

## Current Limitations

- The scenarios are still heuristic and synthetic.
- The calibration metrics are proxy measures over synthetic expectations, not real-world ground truth.
- The markdown table is summary-focused, not publication-grade plotting.
- The CSV is intentionally flat and minimal rather than analysis-framework-specific.
- The SVG figures are lightweight and dependency-free, but not a replacement for final publication plotting.
- Pairwise comparisons are based on saved synthetic run summaries, so they are useful for ablation-style iteration rather than definitive deployment claims.
- Preset orchestration improves reproducibility, but it still operates on heuristic synthetic pipelines rather than calibrated study data.
- Preset summaries are designed for traceability and draft reporting, not final statistical claims.
- Preset aggregates are useful for paper-style comparison and framing, but they still summarize heuristic synthetic experiments.
- Threshold sweeps are useful for sensitivity analysis, but they currently vary only numeric score thresholds, not band-based guardrails or feature weights.
- No calibration or confidence intervals are produced yet.
- The artifact format is stable enough for local iteration, but may evolve as the research design matures.
