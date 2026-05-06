# SignalLock — Project Status and Research Reference

**Last updated:** 2026-05-06 (revision 9 — reviewer package + multi-review calibration summaries)
**Verified test suite:** 201 tests passing in the repository `.venv`
**Python:** 3.11+ required; developed and verified on Python 3.13 in `.venv/`
**Optional dependencies:**
- ML: `pip install signallock[ml]` (scikit-learn ≥ 1.3)
- API: `pip install signallock[api]` (fastapi ≥ 0.110, uvicorn ≥ 0.27, pydantic ≥ 2.5)
- Dashboard: Next.js 15 + TypeScript + Tailwind in `dashboard/` (Node.js ≥ 18, install via `cd dashboard && npm install`)

## Development Environment

This repository ships with a `.venv/` directory created from `python3.13 -m venv .venv`. To bootstrap from scratch:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[ml,api]" httpx
```

Run all commands using `.venv/bin/python -m signallock <command>` after an editable install, or use `PYTHONPATH=src .venv/bin/python -m signallock <command>` directly from the repo checkout.

---

## Purpose of This Document

This file is a living research and engineering reference for:

1. **Paper writing** — what has been built, which results map to which research questions, what numbers to cite.
2. **Agent handoff** — what every module does, what CLI commands exist, what the schemas are, and exactly what to build next.

Read this file before making any code changes. Update it whenever something significant is added.

All quantitative findings in this document should be treated as **synthetic-data or proxy-evaluation results** unless a section explicitly says otherwise. They are useful for prototype iteration and thesis planning, but they are not a substitute for real-world validation.

---

## Research Questions

| RQ | Question | Status |
|---|---|---|
| RQ1 | Can public OSINT materially improve defensive prediction of targeted password risk beyond generic password meters? | Prototype ML pipeline implemented; current deltas are measured on synthetic labeled scenarios only |
| RQ2 | Does separating exposure risk from password predictability produce better calibrated security decisions? | Separation implemented; proxy calibration and threshold sweeps are in place for synthetic evaluation |
| RQ3 | Can a combined model improve enterprise authentication hardening without excessive false positives? | Policy engine implemented; false-positive proxy rates are tracked, but field validation is still pending |
| RQ4 | Are OSINT-aware explanations more actionable than generic strength-meter feedback? | Explanation renderer and expert-review scaffolding implemented; actionability has not yet been validated with a real study |

---

## Core Design Principle (Never Violate)

`Exposure Risk` and `Password Predictability Risk` are scored **separately** and only combined at the **policy layer**.

- `ExposureAssessment` — how targetable is the account?
- `PasswordRiskAssessment` — how predictable is this password given that exposure?
- `HardeningRecommendation` — the policy engine combines both scores into an action.

If any code change makes the tool better at **offensive targeting** than at **defensive measurement**, redesign before committing.

---

## What Has Been Built

### Layer 1 — Core Scoring Pipeline

| Module | Purpose |
|---|---|
| `src/signallock/schemas.py` | All dataclasses and enums (~1600 lines, 40+ types). The canonical definition for every data shape in the project. |
| `src/signallock/synthetic_profiles.py` | Generates reproducible `PublicProfile` instances with varied seniority, department, platform presence, usernames, interests, and years. |
| `src/signallock/exposure.py` | `PublicProfile` → `AttributeVector` → `ExposureAssessment`. Heuristic component scoring: seniority weight, platform surface, identity surface, temporal tokens, org context, discoverability bonus. Score 0–100, four bands. |
| `src/signallock/password_risk.py` | `PublicProfile + password` → `PasswordRiskAssessment`. Generic signals (length, diversity, sequences) + contextual signals (token overlaps with name, org, year, username, location/interests). Stores `matched_tokens` — the actual profile tokens found in the password. |
| `src/signallock/policy.py` | `ExposureAssessment + PasswordRiskAssessment` → `HardeningRecommendation`. Weighted combined score, threshold-driven primary action selection, supporting action list. Three named policy profiles loaded from `configs/policy_profiles.json`. |

### Layer 2 — Explanation Renderer

| Module | Purpose |
|---|---|
| `src/signallock/explanation.py` | Template-based human-readable explanations. `explain_exposure` → `ExposureExplanation` (summary + per-factor sentences using real profile data). `explain_password_risk` → `PasswordRiskExplanation` (uses `matched_tokens` for specificity without echoing the password, and reflects the effective ML-assisted band when policy overrides the heuristic band). `explain_hardening` → `HardeningExplanation` (action sentence + composed paragraph). Deterministic, no LLM dependency. |

**Key design:** Every explanation uses the actual profile data (name, title, org, platform count, year, matched tokens) — not generic templates. The password is never echoed; only matched token strings are mentioned.

### Layer 3 — Evaluation and Calibration

| Module | Purpose |
|---|---|
| `src/signallock/evaluation.py` | Synthetic scenario specs with `expected_action_floor` and `expected_action_ceiling`. **Ten scenarios per profile** — original five (`contextual_name_year` CRITICAL, `organization_year` HIGH, `interest_year` MEDIUM, `username_suffix` HIGH, `random_strong` LOW) plus five extended variants (`name_only` MEDIUM, `year_only` MEDIUM, `generic_weak` MEDIUM, `interest_only` LOW, `username_year` HIGH). The extended variants create overlapping feature distributions across risk classes for richer ML training data. `PolicyCalibrationSummary` tracks: `within_expected_range_rate`, `under_hardening_rate`, `over_hardening_rate`, `true_positive_proxy_rate`, `false_positive_proxy_rate`, `step_up_or_higher_rate`, `block_or_higher_rate`, `mean_action_severity_gap`. |
| `src/signallock/reporting.py` | Saves timestamped evaluation artifact bundles. Renders calibration and comparison markdown tables. |
| `src/signallock/analysis.py` | Aggregates saved evaluation runs into cross-run score and calibration rows. |
| `src/signallock/comparison.py` | Baseline-vs-candidate policy deltas: action transition counts, score deltas, run-level comparison CSV and SVG. |
| `src/signallock/figures.py` | Lightweight SVG grouped bar charts and stacked action distribution charts from cross-run aggregates. |

### Layer 4 — Experiment Orchestration

| Module | Purpose |
|---|---|
| `src/signallock/presets.py` | Named evaluation presets from `configs/experiment_presets.json`. `execute_preset` runs: evaluation across all seeds → analysis → comparison → figures → manifest. |
| `src/signallock/results.py` | Scans preset manifests and flattens into thesis-friendly tables: per-run, per-policy, per-calibration, per-comparison records with CSV and markdown. |
| `src/signallock/preset_aggregates.py` | Cross-preset aggregation (with std dev) for paper-style result tables: within-preset and cross-preset policy, calibration, and comparison aggregates. |

### Layer 5 — Threshold Sensitivity

| Module | Purpose |
|---|---|
| `src/signallock/threshold_sweeps.py` | Shifts warn/step-up/enforce-MFA thresholds by additive offsets (default: −12, −8, −4, 0, +4, +8, +12). Reports calibration metrics per variant and delta vs reference (offset=0). |
| `src/signallock/threshold_sweep_analysis.py` | Aggregates saved sweep bundles by (base_profile, offset). Cross-run mean calibration metrics. |
| `src/signallock/threshold_sweep_figures.py` | Three SVG line charts: within-range rate, FP proxy rate, action-change rate — all vs threshold offset, one line per policy profile. |
| `src/signallock/sweep_presets.py` | Named sweep presets from `configs/threshold_sweep_presets.json`. `execute_sweep_preset` runs: N seeds × M base_profiles sweep bundles → cross-run analysis → figures → manifest. Three presets: `balanced_sweep` (3 seeds, balanced only), `all_profiles_sweep` (3 seeds, all profiles), `fine_sweep` (5 seeds, all profiles, finer offsets). |

### Layer 6 — ML Pipeline

| Module | Purpose |
|---|---|
| `src/signallock/dataset.py` | Generates labeled feature-matrix CSV for ML training. One row per (profile, scenario). 18 numeric feature columns + 3 scores + 3 band/action labels + 4 severity/calibration columns. `_csv_rows_to_records` reconstructs records from saved CSV. |
| `src/signallock/model.py` | scikit-learn classifier (optional dep). `extract_features` maps `AttributeVector + PasswordRiskAssessment` → 18-column feature dict. `train_model` fits logistic or GBT estimator, reports model accuracy, heuristic baseline accuracy, and delta. `train_model_cv` runs stratified k-fold cross-validation and returns mean ± std accuracy for both model and heuristic across folds. `predict_risk_band` for inference. `save_model / load_model_artifacts` for pickle + JSON metadata persistence. |
| `src/signallock/model_integration.py` | End-to-end ML scorer integration. `compare_scoring(password, profile, model_file, config)` runs both heuristic and ML-assisted recommendations on the same input and returns a `ModelScoringComparison` showing where the two approaches agree or diverge on band and action. Used by `recommend-hardening --model-file`, `explain-recommendation --model-file`, and the dedicated `compare-scoring` CLI command. |

### Layer 7 — FastAPI Service

| Module | Purpose |
|---|---|
| `src/signallock/api.py` | Stateless FastAPI service (optional dep). `create_app(model_file=None)` factory builds an app with seven routes (`/healthz`, `/policies`, `/score/exposure`, `/score/password`, `/recommend`, `/explain`, `/compare-scoring`). Pydantic models defined at module level for proper FastAPI introspection. Server stores nothing about callers and never echoes passwords back. Audit Mode uses `/score/exposure` (batch) and `/recommend`; Interactive Mode uses `/score/password`, `/recommend`, and `/explain`. The `/compare-scoring` endpoint and `?ml=true` query mode require the server to be started with `--model-file <pkl>`. |

### Layer 8 — Empirical Calibration Infrastructure

| Module | Purpose |
|---|---|
| `src/signallock/expert_review.py` | Bridges synthetic proxy labels to real expert judgement. `generate_review_tasks(profiles, model_file=None)` produces one `ExpertReviewTask` per (profile, scenario) pair with a one-line `profile_summary`, the candidate password, the heuristic band/action, and optionally an embedded `ml_predicted_band` produced from a saved model. `write_review_tasks_csv` writes an Excel-friendly export with empty `expert_band` / `expert_action` / `notes` columns. `import_expert_ratings_csv` parses a completed CSV back into typed `ExpertRating` records (skips blank rows). `extract_ml_predicted_bands_csv` recovers embedded ML bands from the completed review packet instead of trying to reconstruct them later from partial artifacts. `compute_external_calibration(records, ratings, ml_predicted_bands=None)` returns an `ExternalCalibrationResult` with three-way agreement rates (heuristic vs expert, ML vs expert, heuristic vs ML), severe-disagreement count (≥ 2-band gap), distribution histograms, and per-task disagreement details. This is the layer that lets RQ2/RQ3 graduate from self-referential proxy metrics to expert-validated calibration. |

### Layer 9 — Analyst Dashboard (Next.js 15)

| File | Purpose |
|---|---|
| `dashboard/` | Next.js 15 + TypeScript + Tailwind dashboard. Three pages: org-level exposure heatmap (`/`), per-user drill-down (`/users/[id]`), interactive password tester (`/test`). All data is fetched from the FastAPI backend via the typed client in `lib/api.ts`. Mirrored TypeScript types in `lib/types.ts` keep the wire format aligned with the Python schemas. |
| `dashboard/components/ExposureHeatmap.tsx` | Sortable, filterable table with risk-band counts and color-coded badges. Click a row to drill into the user. |
| `dashboard/components/UserDetailClient.tsx` | Per-user breakdown: exposure score + band, public-platform surface, tenure, top exposure factors, all component scores, full profile snapshot, and the inline interactive password tester. |
| `dashboard/components/PasswordTester.tsx` | Score a candidate password against one profile. Shows password band, combined score, primary action, and the full natural-language explanation paragraph. When the API was started with `--model-file`, also shows a side-by-side heuristic vs ML comparison panel with `bands_agree` / `actions_agree` flags. |
| `dashboard/components/PasswordTesterPage.tsx` | Standalone tester at `/test` — pick any synthetic profile from the roster and evaluate any password against their context. |
| `dashboard/lib/api.ts` | Typed thin client for all seven FastAPI routes. `NEXT_PUBLIC_API_BASE` controls the backend URL (default `http://localhost:8000`). |

**Backend changes for the dashboard:**
- `api.py` accepts `cors_origins: list[str] | None` and adds `CORSMiddleware` when supplied.
- New route: `GET /demo/profiles?count=N&seed=S` generates a synthetic roster for the dashboard's bootstrap (capped at 200 profiles).
- CLI: `signallock serve --cors-origins http://localhost:3000` enables the dashboard's dev server to call the API.

---

## CLI Command Reference

Install: `pip install -e .` or run directly from the checkout with `PYTHONPATH=src .venv/bin/python -m signallock <command>`.

### Scoring and explanation

| Command | What it does |
|---|---|
| `generate-profiles` | Generate synthetic public profiles as JSON |
| `score-exposure` | Score exposure for synthetic profiles |
| `score-password` | Score a candidate password against a profile context |
| `recommend-hardening` | Full pipeline: exposure + password → recommendation; `--model-file` for ML-assisted band |
| `explain-recommendation` | Full pipeline + human-readable explanation paragraph; `--model-file` for ML-assisted band |

### Policy management

| Command | What it does |
|---|---|
| `list-policy-profiles` | List policy profiles and their thresholds |

### Evaluation

| Command | What it does |
|---|---|
| `evaluate-policies` | Run policy evaluation with calibration over synthetic scenarios |
| `analyze-runs` | Aggregate saved evaluation runs |
| `generate-figures` | SVG + CSV figures from saved runs |
| `compare-policies` | Baseline-vs-candidate deltas across runs |

### Preset orchestration (evaluation)

| Command | What it does |
|---|---|
| `list-experiment-presets` | List available evaluation presets |
| `run-preset` | Execute a named evaluation preset end to end |
| `summarize-presets` | Flatten preset bundles into thesis-friendly tables |
| `aggregate-presets` | Cross-preset aggregation for paper tables |

### Threshold sensitivity

| Command | What it does |
|---|---|
| `sweep-thresholds` | Single-run threshold sensitivity study |
| `analyze-threshold-sweeps` | Aggregate saved sweep bundles |
| `generate-threshold-sweep-figures` | SVG figures from sweep aggregates |
| `list-sweep-presets` | List available sweep presets |
| `run-sweep-preset` | Multi-seed, multi-profile sweep preset end to end |

### ML pipeline

| Command | What it does |
|---|---|
| `generate-dataset` | Export labeled feature-matrix CSV for ML training |
| `train-model` | Train logistic or GBT classifier; report model vs heuristic accuracy. `--folds N` runs stratified k-fold cross-validation and reports mean ± std accuracy. |
| `compare-scoring` | Side-by-side heuristic vs ML band and action for one (profile, password) pair |

### Service

| Command | What it does |
|---|---|
| `serve` | Start the FastAPI service (`--host`, `--port`, `--model-file`, `--reload`). Audit Mode and Interactive Mode endpoints. Requires `pip install signallock[api]`. |

### Empirical calibration

| Command | What it does |
|---|---|
| `generate-review-tasks` | Export one (profile, scenario) review task per row as an Excel-friendly CSV (or JSON) for security experts to fill in, optionally embedding `ml_predicted_band` from a saved model |
| `compute-external-calibration` | Read completed expert ratings + dataset records and compute three-way agreement (heuristic vs ML vs expert), using embedded `ml_predicted_band` values from the completed review packet when present |
| `summarize-expert-reviews` | Aggregate multiple completed reviewer CSVs into per-reviewer summaries, consensus-task summaries, and a reviewer-batch overview |

**Total: 26 CLI commands.**

---

## Key Numbers (Paper-Ready)

### Heuristic calibration (5 profiles, seed=1, balanced policy, 5-scenario subset)

| Metric | Value |
|---|---|
| `within_expected_range_rate` | 0.48 |
| `contextual_name_year` `action_severity_gap` | −2 (under-hardening by 2 levels) |

The `contextual_name_year` scenario — a password containing the person's first name and tenure year — is the most dangerous scenario and also the one the heuristic handles worst, under-hardening by 2 severity levels.

### ML model — 5-fold stratified cross-validation (50 profiles × 10 scenarios = 500 records, GBT, seed=1)

This is the **primary paper number**. Cross-validated on the richer 10-scenario dataset gives confidence bounds:

| Metric | Value |
|---|---|
| Model accuracy (mean ± std) | **1.0000 ± 0.0000** |
| Heuristic accuracy (mean ± std) | **0.6880 ± 0.0431** |
| **Accuracy delta (mean)** | **+0.3120** |

Per-fold breakdown: heuristic accuracies range 0.65–0.77 across the five folds, model accuracy is 1.00 every fold.

### Single-split GBT (40 profiles × 5 scenarios — original heuristic-friendly dataset)

| Metric | Value |
|---|---|
| GBT test accuracy | 1.00 |
| Heuristic test accuracy (same test split) | 0.375 |
| **Accuracy delta** | **+0.625** |
| Top feature: `password_length` importance | 0.2257 |
| Top feature: `contextual_structure` importance | 0.2018 |
| Top feature: `contextual_name_overlap` importance | 0.1747 |

### End-to-end ML scorer integration (paper Table 2)

Same input password `"Priya2014!"` against the same profile, balanced policy:

| | Band | Action |
|---|---|---|
| Heuristic | HIGH | WARN (no enforcement) |
| ML-assisted | CRITICAL | REQUIRE_STRONGER_PASSWORD |

The heuristic produces a non-actionable WARN; the ML-assisted policy correctly forces remediation. This is the actionability difference that motivates RQ1 and RQ4.

**Interpretation for paper:** The cross-validated +0.312 accuracy delta is the conservative number to cite — it includes the easier scenarios (`random_strong`, `interest_only`) where the heuristic already does well. The +0.625 single-split number on the original dataset reflects the hard-cases-only view. Both directly answer RQ1.

**Caveat to include in paper:** These results use synthetic scenarios with deterministic feature patterns. A real-world evaluation requires empirically labeled data or a controlled user study.

---

## Schema Inventory (for paper section on system design)

### Core pipeline types

| Schema | Description |
|---|---|
| `PublicProfile` | Organization-approved or synthetic public identity record |
| `AttributeVector` | Normalized token buckets derived from a profile |
| `ExposureAssessment` | Heuristic exposure score, band, component scores, top factors |
| `PasswordRiskAssessment` | Heuristic password risk score, generic signals, contextual signals, matched tokens |
| `HardeningRecommendation` | Combined score, policy action, supporting actions, rationale factors, `ml_assisted` flag indicating whether the band came from a trained model or the heuristic |
| `PolicyConfig` | Threshold and weight configuration for one named policy profile |

### Calibration types

| Schema | Description |
|---|---|
| `SyntheticScenarioSpec` | Password + expected risk band + expected action floor/ceiling |
| `PolicyEvaluationRecord` | One evaluated scenario: bands, action, combined score |
| `PolicyEvaluationSummary` | Aggregate outcomes for one policy profile |
| `PolicyCalibrationSummary` | Proxy calibration metrics: within-range rate, FP/TP proxy rates, severity gap |

### Experiment artifact types

| Schema | Description |
|---|---|
| `EvaluationArtifacts` | Filesystem paths for one evaluation run bundle |
| `EvaluationRunSummaryRecord` | Flattened cross-run policy row |
| `EvaluationRunCalibrationRecord` | Flattened cross-run calibration row |
| `AnalysisArtifacts` | Paths for cross-run analysis bundle |
| `ComparisonArtifacts` | Paths for baseline-vs-candidate comparison bundle |
| `FigureArtifacts` | Paths for SVG/CSV figure bundle |

### Preset types

| Schema | Description |
|---|---|
| `ExperimentPreset` | Named evaluation preset: org, profile_count, seeds, policy_profiles, baseline, candidates |
| `PresetExecutionSummary` | Full outcome of one preset run |
| `PresetArtifacts` | Top-level directories and manifest for one preset |
| `PresetRunRecord` | Flattened preset execution for thesis tables |
| `PresetPolicySummaryRecord` | Per-policy aggregate from one preset |
| `PresetCalibrationSummaryRecord` | Per-policy calibration aggregate from one preset |
| `PresetComparisonSummaryRecord` | Per-candidate comparison row from one preset |
| `PresetResultsOverview` | Metadata for a preset summary operation |
| `PresetAggregateOverview` | Metadata for cross-preset aggregation |

### Threshold sweep types

| Schema | Description |
|---|---|
| `ThresholdSweepPreset` | Named sweep preset: seeds, base_profiles, threshold_offsets |
| `ThresholdSweepRecord` | One threshold variant: score metrics + calibration metrics + reference deltas |
| `ThresholdSweepOverview` | Metadata for one sweep experiment |
| `ThresholdSweepArtifacts` | Paths for one sweep bundle |
| `ThresholdSweepRunRecord` | Flattened row from a saved sweep bundle |
| `ThresholdSweepAggregateRecord` | Cross-run aggregate grouped by (base_profile, offset) |
| `ThresholdSweepAnalysisOverview` | Metadata for a sweep analysis operation |
| `ThresholdSweepAnalysisArtifacts` | Paths for sweep analysis bundle |
| `ThresholdSweepFigureArtifacts` | Paths for sweep figure bundle |
| `SweepPresetArtifacts` | Directories and manifest for one sweep preset execution |
| `SweepPresetExecutionSummary` | Full outcome of one sweep preset run |

### Explanation types

| Schema | Description |
|---|---|
| `ExposureExplanation` | Summary sentence + per-factor sentences using real profile data |
| `PasswordRiskExplanation` | Summary sentence + per-factor sentences using matched token data |
| `HardeningExplanation` | Action sentence + nested sub-explanations + full paragraph |

### Dataset and ML types

| Schema | Description |
|---|---|
| `DatasetRecord` | One labeled training row: 18 features + 3 scores + bands/actions + labels + severity columns |
| `DatasetOverview` | Record count, scenario count, within-range rate, distributions |
| `DatasetArtifacts` | Paths to dataset_records.csv and dataset_overview.json |
| `ModelTrainingResult` | model_type, accuracy, heuristic_accuracy, accuracy_delta, class_report, feature_importances or coefficients |
| `ModelCVResult` | model_type, n_folds, mean ± std accuracy for both model and heuristic, per-fold breakdown |
| `ModelArtifacts` | Paths to .pkl model file and model_metadata.json |
| `ModelScoringComparison` | Side-by-side heuristic vs ML for one (profile, password) pair: bands, actions, agreement booleans, both full recommendations |

### Empirical-calibration types

| Schema | Description |
|---|---|
| `ExpertReviewTask` | One row sent to a security expert for rating: profile summary, password, heuristic reference band, blank fields for `expert_band` / `expert_action` / `notes` |
| `ExpertRating` | One completed rating: `expert_band` (required), `expert_action` (optional), free-form `notes` |
| `ExternalCalibrationResult` | Three-way agreement output: `heuristic_vs_expert_match_rate`, `ml_vs_expert_match_rate`, `heuristic_vs_ml_match_rate`, severe-disagreement count, per-source band distributions, transition counts, disagreement details |
| `ModelScoringComparison` | Side-by-side: heuristic band/action vs ML band/action, bands_agree, actions_agree, both full recommendations |

---

## Test Coverage

**190 tests across the current suite.** All tests pass with `.venv/bin/python -m unittest discover -s tests -v`.

Model tests (`test_model.py`) are decorated `@unittest.skipUnless(_SKLEARN_AVAILABLE, ...)` so they are skipped gracefully if scikit-learn is not installed.

| Test file | What it covers |
|---|---|
| `test_schemas.py` | PublicProfile validation and serialization |
| `test_synthetic_profiles.py` | Generation count, reproducibility, JSON output |
| `test_exposure.py` | AttributeVector normalization, high vs low visibility scoring |
| `test_password_risk.py` | Contextual password scores higher than random; all assessment fields |
| `test_policy.py` | Low-risk ALLOW, high-context REQUIRE_STRONGER_PASSWORD, profile ordering, file override |
| `test_evaluation.py` | Scenario generation, policy comparison, calibration proxy metrics |
| `test_reporting.py` | Markdown table rendering, artifact file creation |
| `test_analysis.py` | Cross-run flattening, CSV and analysis bundle |
| `test_comparison.py` | Per-run deltas, comparison bundle |
| `test_figures.py` | SVG content, aggregate CSV, figure bundle |
| `test_presets.py` | Preset loading, full bundle execution |
| `test_results.py` | Preset manifest scanning, flattened tables |
| `test_preset_aggregates.py` | Within-preset and cross-preset aggregation |
| `test_threshold_sweeps.py` | Sorted variants, calibration metrics, artifact bundle |
| `test_threshold_sweep_analysis.py` | Row flattening, offset aggregation, analysis bundle |
| `test_threshold_sweep_figures.py` | SVG content, figure bundle |
| `test_sweep_presets.py` | Preset loading, multi-seed × multi-profile run count, manifest, figures |
| `test_explanation.py` | Exposure/password/hardening explanations, factor sentences, full paragraph, JSON |
| `test_dataset.py` | Record count arithmetic, feature types, score bounds, calibration consistency, CSV structure, artifact persistence |
| `test_model.py` | Both estimator types, accuracy metrics, delta formula, feature importances, inference, persistence round-trip |
| `test_model_integration.py` | ML band override in policy, `ml_assisted` flag, combined score preservation, compare_scoring, serialization |
| `test_cli.py` | All major CLI commands |
| `test_expert_review.py` | Review task generation, CSV/JSON export, rating import (partial completion, invalid bands), three-way calibration computation, ML-band integration, no-overlap error path |
| `test_api.py` | FastAPI service endpoints (heuristic mode + ML-backed mode), validation errors, 503 responses when model not loaded |

---

## Artifact Directory Layout

```
artifacts/
├── datasets/
│   └── <timestamp>/
│       ├── dataset_records.csv       ← 35-column feature matrix (ML training data)
│       └── dataset_overview.json
├── evaluations/
│   └── <timestamp>/
│       ├── report.json
│       ├── summaries.json
│       ├── comparison_table.md
│       ├── calibration_summaries.json
│       └── calibration_table.md
├── analysis/
│   └── <timestamp>/
│       ├── analysis.json
│       ├── comparison_table.md
│       ├── policy_matrix.csv
│       ├── calibration_table.md
│       └── calibration_matrix.csv
├── comparisons/
│   └── <timestamp>/
│       ├── comparison_summary.json
│       ├── comparison_table.md
│       ├── run_deltas.csv
│       └── comparison_deltas.svg
├── figures/
│   └── <timestamp>/
│       ├── figure_summary.json
│       ├── policy_aggregates.csv
│       ├── policy_summary_table.md
│       ├── policy_score_summary.svg
│       └── policy_action_summary.svg
├── presets/
│   └── <timestamp>-<preset>/
│       ├── preset_manifest.json
│       ├── evaluations/
│       ├── analysis/
│       ├── comparisons/
│       └── figures/
├── results/
│   └── <timestamp>/
│       ├── preset_results_summary.json
│       ├── preset_runs.csv
│       ├── preset_policy_summaries.csv
│       ├── preset_calibration_summaries.csv
│       └── preset_comparison_summaries.csv
├── preset_aggregates/
│   └── <timestamp>/
│       ├── preset_aggregate_summary.json
│       ├── preset_policy_aggregates.csv
│       ├── cross_preset_policy_aggregates.csv
│       └── (+ calibration and comparison CSVs and markdown tables)
├── threshold_sweeps/
│   └── <timestamp>/
│       ├── threshold_sweep_summary.json
│       ├── threshold_sweep_records.csv
│       └── threshold_sweep_table.md
├── threshold_sweep_analysis/
│   └── <timestamp>/
│       ├── threshold_sweep_analysis.json
│       ├── threshold_sweep_rows.csv
│       ├── threshold_sweep_aggregates.csv
│       └── (+ markdown tables)
├── threshold_sweep_figures/
│   └── <timestamp>/
│       ├── threshold_sweep_figure_summary.json
│       ├── threshold_sweep_within_range.svg
│       ├── threshold_sweep_false_positive.svg
│       └── threshold_sweep_action_change.svg
├── sweep_presets/
│   └── <timestamp>-<preset>/
│       ├── sweep_preset_manifest.json
│       ├── sweeps/
│       ├── analysis/
│       └── figures/
└── models/
    └── <timestamp>/
        ├── model_gradient_boosting.pkl   ← or model_logistic.pkl
        └── model_metadata.json
```

All artifact directories are gitignored. Reproduce any run with the same `--seed` and `--count` flags.

---

## Config Files

| File | Contents |
|---|---|
| `configs/policy_profiles.json` | balanced, strict, usability — thresholds and weights |
| `configs/experiment_presets.json` | baseline_matrix (3 seeds, all profiles), strict_focus (4 seeds), usability_focus (4 seeds) |
| `configs/threshold_sweep_presets.json` | balanced_sweep (3 seeds), all_profiles_sweep (3 seeds, all profiles), fine_sweep (5 seeds, finer offsets) |

---

## What Is Not Built Yet (Next Steps)

Listed in priority order.

### 1. ✅ End-to-end ML scorer integration — DONE

`recommend_hardening` now accepts `predicted_password_band: RiskBand | None = None`. When supplied, it overrides the heuristic band for all policy decisions while keeping the heuristic numeric score for the combined score calculation. `HardeningRecommendation` gains `ml_assisted: bool = False`.

New CLI commands:
- `recommend-hardening --model-file <pkl>` — ML-assisted recommendation
- `compare-scoring --model-file <pkl>` — side-by-side heuristic vs ML output (the paper table)

Concrete result on `"Priya2014!"` (seed=1, profile-index=0, balanced):
- Heuristic: `password_band=HIGH`, `action=WARN`
- ML: `password_band=CRITICAL`, `action=REQUIRE_STRONGER_PASSWORD`
- `bands_agree=False`, `actions_agree=False`

This is the result that goes in Table 1 of the paper.

### 2. ✅ Larger synthetic dataset and cross-validation — DONE

`evaluation.py` now generates **10 scenarios per profile** (5 original + 5 extended: `name_only`, `year_only`, `generic_weak`, `interest_only`, `username_year`). The extended scenarios decouple feature patterns from scenario identity (e.g., name without year, year without name) so the classifier learns feature-to-label mappings rather than scenario-template-to-label mappings.

`train_model_cv` runs stratified k-fold CV and reports mean ± std accuracy for both model and heuristic across all folds. CLI: `train-model --folds N`.

Concrete result on 50 profiles × 10 scenarios = 500 records, 5-fold stratified CV, GBT, seed=1:
- Model: 1.0000 ± 0.0000
- Heuristic: 0.6880 ± 0.0431
- **Delta: +0.3120** (the conservative paper number — includes easier scenarios where the heuristic does well)

### 3. ✅ FastAPI service layer — DONE

`src/signallock/api.py` implements a stateless FastAPI service with seven routes:

| Route | Purpose |
|---|---|
| `GET /healthz` | Liveness check + `model_loaded` flag |
| `GET /policies` | List the three named policy profiles and thresholds |
| `POST /score/exposure` | Audit-mode batch endpoint: list of profiles → list of `ExposureAssessment` |
| `POST /score/password` | Interactive-mode endpoint: profile + password → `PasswordRiskAssessment` |
| `POST /recommend` | Full pipeline; pass `?ml=true` for ML-assisted band (requires `--model-file` at startup) |
| `POST /explain` | Full pipeline + human-readable paragraph; same `?ml=true` toggle |
| `POST /compare-scoring` | Side-by-side heuristic vs ML output (requires `--model-file` at startup) |

CLI: `signallock serve --port 8000 [--model-file <pkl>]`. Tests use FastAPI's `TestClient` with no live server. The optional dep group is `signallock[api]`.

### 4. ✅ Empirical calibration infrastructure — DONE

`src/signallock/expert_review.py` ships the full pipeline an empirical study needs:

| Step | Tool |
|---|---|
| Export tasks | `signallock generate-review-tasks --count N --seed S --model-file <pkl> --format csv --output-file tasks.csv` |
| Hand to experts | The CSV has rating columns (`expert_band`, `expert_action`, `notes`) intentionally blank for the reviewer to fill in |
| Re-import | `import_expert_ratings_csv(path)` returns typed `ExpertRating` records, silently skipping blank rows |
| Compute calibration | `signallock compute-external-calibration --records-file <records.csv> --ratings-file <ratings.csv> [--model-file <pkl>] --pretty` |

The result includes `heuristic_vs_expert_match_rate`, `ml_vs_expert_match_rate` (when the completed review packet carries `ml_predicted_band` values), `severe_disagreement_count` (≥ 2-band gap), per-band distributions for all three sources, and a list of disagreement details with notes — everything required for the paper's calibration table and qualitative discussion. See [`docs/EXPERT_REVIEW_PROTOCOL.md`](EXPERT_REVIEW_PROTOCOL.md) for the recommended provenance-preserving workflow.

**Note for the paper:** This layer is *infrastructure*, not data. Running an actual study (collecting ratings from N security professionals across M scenarios) is still future work. The infrastructure makes that study tractable rather than ad-hoc.

### Deployment

The repository is **Railway + Vercel ready**. The backend deployment path is now Dockerfile-based for deterministic packaging. See [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) for the full step-by-step guide.

| Layer | Platform | Files |
|---|---|---|
| Backend (FastAPI) | Railway | `Dockerfile`, `.dockerignore`, `railway.json` |
| Frontend (Next.js) | Vercel | `dashboard/vercel.json` |

The `serve` CLI reads `PORT`, `HOST`, `MODEL_FILE`, and `CORS_ORIGINS` from environment variables, and the Docker deployment path starts the API with `python -m signallock serve --host 0.0.0.0`.

### 5. ✅ Analyst dashboard — DONE

`dashboard/` ships a Next.js 15 + TypeScript + Tailwind app with three pages:

| Route | What it does |
|---|---|
| `/` | Org-level exposure heatmap. Configurable roster size + seed. Filter by band, sort by band/score/name. Each row shows employee, title, department, exposure score, color-coded band, top factor, drill-in link. |
| `/users/[id]` | Per-user drill-down: exposure score header card, public-platform surface card, tenure card, top exposure factor list with ranking, all component scores, full profile snapshot, inline interactive password tester. |
| `/test` | Standalone password tester: pick any profile from the roster, type a candidate password, see heuristic + (optional) ML scoring side by side with the full natural-language explanation paragraph. |

**Verified:** Production build (`npm run build`) compiles all 5 routes clean. Live integration test confirmed:
- Dashboard renders with all branding and nav
- API `/demo/profiles` returns synthetic roster
- API `/score/exposure` returns batch assessments (e.g. `Priya Hughes: 47.5/MEDIUM`)
- CORS preflight succeeds: `access-control-allow-methods: GET, POST, OPTIONS`

**Run it:**

```bash
# Terminal 1 — API with CORS for the dashboard's dev port
.venv/bin/python -m signallock serve --port 8000 --cors-origins http://localhost:3000

# Terminal 2 — Next.js dev server
cd dashboard && npm install && npm run dev
```

Open `http://localhost:3000`. To enable the ML-assisted toggle and side-by-side comparison panel, add `--model-file <pkl>` to the serve command.

---

## Paper Section Hooks

| Paper section | What to cite / point to |
|---|---|
| Introduction | 48% within-range rate of heuristic baseline; `contextual_name_year` gap of −2 motivates the problem |
| Related Work | Cite targeted guessing literature from `proposal/references.bib`; SignalLock is the defensive counterpart |
| System Design | Section 3: data flow diagram from `docs/ARCHITECTURE.md`; schema table from this document |
| Exposure Engine | Section 4.1: `exposure.py` component weights table; SENIORITY_WEIGHTS, COMPONENT_LABELS |
| Password Risk Engine | Section 4.2: `password_risk.py` signal tables; GENERIC_LABELS, CONTEXT_LABELS |
| Policy Engine | Section 4.3: three profiles from `configs/policy_profiles.json`; threshold table |
| Explanation Layer | Section 4.4: example output from `explain-recommendation --password "Priya2014!" --seed 1 --profile-index 0` |
| Evaluation | Section 5: `within_expected_range_rate`, FP/TP proxy rates per policy; threshold sweep figures |
| ML Baseline Comparison | Section 6: +0.625 accuracy delta table; top-5 feature importances table |
| Limitations | Synthetic scenarios, proxy calibration, no real-world deployment data |

---

## Quick Reproduction Commands

```bash
# Install (Python 3.13 venv recommended)
python3.13 -m venv .venv
.venv/bin/python -m pip install -e .                # core only
.venv/bin/python -m pip install -e ".[ml]"          # with ML support
.venv/bin/python -m pip install -e ".[ml,api]"      # with ML + API service

# Run all tests
.venv/bin/python -m unittest discover -s tests -v

# Full evaluation preset
.venv/bin/python -m signallock run-preset --preset baseline_matrix --pretty

# Threshold sensitivity study
.venv/bin/python -m signallock run-sweep-preset --preset all_profiles_sweep --pretty

# Generate dataset and train model
.venv/bin/python -m signallock generate-dataset --count 50 --seed 1 --save-dataset
.venv/bin/python -m signallock train-model --count 50 --seed 1 \
  --model-type gradient_boosting --save-model --pretty

# Cross-validated training (paper Table 1)
.venv/bin/python -m signallock train-model --count 50 --seed 1 \
  --model-type gradient_boosting --folds 5 --pretty

# ML-assisted recommendation (uses trained model)
.venv/bin/python -m signallock recommend-hardening \
  --password "Priya2014!" --seed 1 --profile-index 0 \
  --policy-profile balanced --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl --pretty

# Heuristic vs ML side-by-side (paper Table 2)
.venv/bin/python -m signallock compare-scoring \
  --password "Priya2014!" --seed 1 --profile-index 0 \
  --policy-profile balanced --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl --pretty

# Explanation example
.venv/bin/python -m signallock explain-recommendation \
  --password "Priya2014!" --seed 1 --profile-index 0 \
  --policy-profile balanced --pretty

# Start the FastAPI service (Audit + Interactive mode endpoints)
.venv/bin/python -m signallock serve --port 8000 \
  --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl

# Then from another terminal:
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/policies

# Empirical calibration workflow
.venv/bin/python -m signallock generate-review-tasks \
  --count 50 --seed 1 \
  --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl \
  --format csv --output-file tasks.csv
# (security experts fill in expert_band column)
.venv/bin/python -m signallock generate-dataset --count 50 --seed 1 --save-dataset
.venv/bin/python -m signallock compute-external-calibration \
  --records-file artifacts/datasets/<timestamp>/dataset_records.csv \
  --ratings-file completed_tasks.csv \
  --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl \
  --pretty
```

---

## Repository

- GitHub: <https://github.com/sagarkishore-7/signallock>
- License: Apache-2.0
- Contact: contact@matrixsociallabs.com
