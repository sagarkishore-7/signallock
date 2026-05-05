# SignalLock Architecture

## Purpose

This document summarizes the current prototype architecture and how the repository maps to the research design.

## Current Data Flow

The implemented Phase 1 flow is:

`Synthetic PublicProfile -> AttributeVector -> ExposureAssessment`

and now:

`Synthetic PublicProfile + candidate password -> PasswordRiskAssessment`

and:

`ExposureAssessment + PasswordRiskAssessment -> HardeningRecommendation`

and:

`Synthetic profile batch + policy profiles -> PolicyEvaluationSummary`

and now:

`synthetic scenario expectations + PolicyEvaluationRecord -> PolicyCalibrationSummary`

and now:

`PolicyEvaluationSummary + PolicyCalibrationSummary + PolicyEvaluationRecord -> timestamped evaluation artifacts`

and:

`saved evaluation artifacts -> cross-run analysis rows -> markdown/CSV analysis bundle`

and now:

`saved evaluation artifacts -> cross-run calibration rows -> markdown/CSV calibration bundle`

and now:

`cross-run analysis rows -> aggregate policy metrics -> SVG/CSV figure bundle`

and:

`cross-run analysis rows -> baseline/candidate matching -> policy comparison bundle`

and:

`named experiment preset -> evaluation runs + analysis + comparison + figures`

and now:

`saved preset manifests -> preset-level policy/comparison summaries -> thesis-friendly markdown/CSV bundle`

and now:

`preset summary bundles -> within-preset and cross-preset aggregates -> paper-style result tables`

and now:

`synthetic profile batch + one base policy profile -> threshold-shifted policy variants -> threshold-sweep calibration summary bundle`

These are still heuristic baselines, but they establish the core separation the project depends on:

- exposure risk,
- password predictability risk,
- later, a combined policy layer.

## Implemented Modules

### `src/signallock/synthetic_profiles.py`

Responsibilities:

- generate reproducible synthetic public profiles,
- vary seniority, department, platform presence, usernames, interests, and years,
- provide JSON export for experiments.

### `src/signallock/schemas.py`

Responsibilities:

- define shared enums and dataclasses,
- normalize profile fields and token buckets,
- provide structured outputs for exposure and password-risk assessments.

### `src/signallock/exposure.py`

Responsibilities:

- convert a `PublicProfile` into an `AttributeVector`,
- compute a transparent heuristic exposure score,
- surface component-level factors for explainability.

### `src/signallock/password_risk.py`

Responsibilities:

- score a candidate password against a public profile context,
- combine generic weakness signals with context-overlap signals,
- return bounded risk bands and interpretable factors.

### `src/signallock/policy.py`

Responsibilities:

- combine exposure and password-risk outputs,
- map them to a primary hardening action,
- attach supporting actions such as MFA or awareness prioritization,
- surface concise rationale for the recommendation,
- support multiple named policy profiles for experiments,
- load profile thresholds from a JSON config file.

### `src/signallock/evaluation.py`

Responsibilities:

- generate safe synthetic password scenarios for evaluation only,
- attach proxy expectation ranges to those synthetic scenarios,
- compare multiple policy profiles over the same synthetic profile batch,
- emit summary metrics, proxy calibration metrics, and optional detailed records.

### `src/signallock/reporting.py`

Responsibilities:

- render aggregate policy comparisons as markdown tables,
- render proxy calibration summaries as markdown tables,
- save evaluation runs to timestamped local artifact bundles,
- keep experiment outputs reproducible without exposing them in git.

### `src/signallock/analysis.py`

Responsibilities:

- scan saved evaluation runs from disk,
- flatten per-run policy summaries into comparison-friendly rows,
- flatten per-run calibration summaries into comparison-friendly rows,
- render cross-run markdown and CSV outputs,
- save timestamped analysis bundles for later research work.

### `src/signallock/comparison.py`

Responsibilities:

- match baseline and candidate policy rows within the same saved run,
- compute run-level deltas and aggregate comparison summaries,
- render markdown, CSV, and lightweight SVG delta outputs,
- save timestamped comparison bundles for ablation-style analysis.

### `src/signallock/presets.py`

Responsibilities:

- load named experiment presets from configuration,
- execute multi-seed evaluation suites,
- orchestrate downstream analysis, comparisons, and figures,
- save one manifest-driven bundle for reproducible experiment reruns.

### `src/signallock/figures.py`

Responsibilities:

- aggregate cross-run policy metrics,
- render lightweight SVG score and action charts,
- emit aggregate CSV and markdown summary tables,
- save timestamped figure bundles for reports and thesis drafts.

### `src/signallock/cli.py`

Responsibilities:

- expose prototype workflows through a simple CLI,
- generate synthetic profiles,
- score exposure,
- score candidate passwords against synthetic profile context.

### `src/signallock/results.py`

Responsibilities:

- scan executed preset bundles from disk,
- flatten preset runs, per-policy aggregates, and preset-level comparisons,
- flatten per-policy preset calibration summaries,
- render thesis-friendly markdown tables and CSV outputs,
- save timestamped preset-results summary bundles for later analysis and writing.

### `src/signallock/preset_aggregates.py`

Responsibilities:

- aggregate preset-summary outputs across repeated preset executions,
- compute within-preset and cross-preset policy/calibration/comparison summaries,
- render paper-style markdown tables and CSV outputs,
- save timestamped aggregate bundles for thesis and report preparation.

### `src/signallock/threshold_sweeps.py`

Responsibilities:

- load one base policy profile for sensitivity analysis,
- generate threshold-shifted variants without mutating the underlying config file,
- evaluate each variant against the same synthetic profile batch,
- render markdown and CSV sweep summaries,
- save timestamped threshold-sweep bundles for threshold-tuning and calibration review.

## Current Output Types

### `PublicProfile`

Represents organization-approved or synthetic public-facing identity data.

### `AttributeVector`

Represents normalized tokens derived from profile data.

### `ExposureAssessment`

Represents a baseline exposure score and component-level contributing factors.

### `PasswordRiskAssessment`

Represents a baseline candidate-password risk score, component-level signals, and matched contextual tokens.

### `HardeningRecommendation`

Represents a baseline policy output that combines both risk layers.

### `PolicyEvaluationSummary`

Represents aggregate outcomes for one policy profile over a synthetic evaluation run.

### `ThresholdSweepRecord`

Represents one threshold-shifted policy variant together with score, calibration, and reference-delta metrics.

### `ThresholdSweepOverview`

Represents the metadata for one threshold-sweep experiment, including base profile and offsets.

### `ThresholdSweepArtifacts`

Represents the saved filesystem outputs for one timestamped threshold-sweep bundle.

### `PolicyCalibrationSummary`

Represents proxy calibration outcomes for one policy profile over a synthetic evaluation run.

### `EvaluationArtifacts`

Represents the saved filesystem outputs for one timestamped experiment run.

### `EvaluationRunSummaryRecord`

Represents one flattened policy summary row from one saved evaluation run.

### `EvaluationRunCalibrationRecord`

Represents one flattened calibration summary row from one saved evaluation run.

### `EvaluationRunAnalysisOverview`

Represents top-level metadata for a cross-run analysis operation.

### `AnalysisArtifacts`

Represents the saved filesystem outputs for one timestamped cross-run analysis bundle.

### `PolicyComparisonOverview`

Represents high-level metadata for one baseline-versus-candidate comparison batch.

### `PolicyComparisonRunDelta`

Represents one per-run delta between a baseline policy and a candidate policy.

### `PolicyComparisonSummary`

Represents aggregate candidate-versus-baseline deltas across matched runs.

### `ComparisonArtifacts`

Represents the saved filesystem outputs for one timestamped policy comparison bundle.

### `ExperimentPreset`

Represents a named, versionable experiment configuration.

### `PresetArtifacts`

Represents the top-level directories and manifest for one preset execution.

### `PresetExecutionSummary`

Represents the combined outcome of one preset run across all downstream artifact types.

### `PolicyAggregateRecord`

Represents cross-run aggregate metrics for one policy profile.

### `FigureArtifacts`

Represents the saved filesystem outputs for one timestamped figure bundle.

### `PresetRunRecord`

Represents one flattened preset execution record for later analysis and reporting.

### `PresetPolicySummaryRecord`

Represents one per-policy aggregate row extracted from a preset execution.

### `PresetCalibrationSummaryRecord`

Represents one per-policy calibration row extracted from a preset execution.

### `PresetComparisonSummaryRecord`

Represents one per-candidate comparison row extracted from a preset execution.

### `PresetResultsOverview`

Represents high-level metadata for aggregated preset-summary operations.

### `PresetResultsArtifacts`

Represents the saved filesystem outputs for one timestamped preset-results bundle.

### `PresetPolicyAggregateRecord`

Represents one within-preset aggregate row for a policy profile.

### `PresetCalibrationAggregateRecord`

Represents one within-preset aggregate row for calibration behavior.

### `PresetComparisonAggregateRecord`

Represents one within-preset aggregate row for a baseline-versus-candidate comparison.

### `CrossPresetPolicyAggregateRecord`

Represents one policy-level aggregate row across multiple preset families.

### `CrossPresetCalibrationAggregateRecord`

Represents one calibration-level aggregate row across multiple preset families.

### `CrossPresetComparisonAggregateRecord`

Represents one comparison-level aggregate row across multiple preset families.

### `PresetAggregateOverview`

Represents high-level metadata for one preset aggregate analysis operation.

### `PresetAggregateArtifacts`

Represents the saved filesystem outputs for one timestamped preset aggregate bundle.

## Current Prototype Boundaries

The current prototype intentionally:

- uses synthetic public-profile contexts by default,
- scores risk rather than generating guesses,
- avoids storing passwords beyond immediate evaluation,
- keeps exposure and password risk separate.

The current prototype does not yet:

- train or use ML models,
- ingest live OSINT sources,
- implement analyst dashboards,
- run user studies or calibration experiments.

The current prototype does support:

- file-backed policy profiles under `configs/policy_profiles.json`,
- comparative CLI evaluation across multiple profiles,
- optional custom policy files for experiments,
- threshold-sensitivity experiments without hand-editing policy configs,
- timestamped local artifact bundles for reproducible evaluation runs,
- cross-run markdown and CSV exports derived from saved runs,
- baseline-versus-candidate comparison bundles derived from matched runs,
- dependency-light SVG figure bundles derived from cross-run aggregates,
- preset-driven orchestration across the full experiment workflow.
- preset-level summary bundles for higher-level experiment reporting.
- paper-style aggregate bundles for higher-level cross-preset interpretation.

## Near-Term Architecture Expansion

The next likely modules are:

- explanation renderer,
- password feature calibration support,
- dataset generation for controlled evaluation,
- richer statistical evaluation beyond lightweight SVG and CSV outputs.

## CLI-Oriented Workflow

Today the repository is CLI-first. A typical prototype loop is:

1. Generate synthetic profiles.
2. Score exposure for those profiles.
3. Score a candidate password against one profile context.
4. Apply a named hardening policy profile.
5. Compare multiple policy profiles over the same synthetic scenarios.
6. Save the run and inspect the generated artifact bundle.
7. Aggregate multiple runs into cross-run analysis outputs.
8. Compare baseline and candidate policy profiles.
9. Generate score and action figures for research communication.
10. Execute named presets for reproducible end-to-end experiment suites.
11. Sweep policy thresholds to inspect calibration sensitivity before changing defaults.

That keeps the implementation transparent and testable before introducing more complex modeling.
