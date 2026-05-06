# SignalLock

SignalLock is a research-driven defensive security project for OSINT-calibrated password risk assessment and context-aware enterprise authentication hardening.

The project combines two ideas that are usually treated separately:

1. Public exposure risk: how much publicly available information increases the likelihood that an account will be targeted.
2. Password predictability risk: how much a candidate password becomes easier to guess when conditioned on that public exposure.

The long-term goal is a privacy-conscious toolchain that helps defenders:

- prioritize high-exposure accounts,
- give personalized password guidance,
- trigger adaptive authentication controls,
- and explain why a user or password is risky without generating exploit-ready guesses.

## Project Status

This repository is now in early prototype implementation.

Current contents:

- a detailed implementation roadmap under [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md),
- a current architecture summary under [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
- a data-governance note under [`docs/DATA_POLICY.md`](docs/DATA_POLICY.md),
- a policy-profile reference under [`docs/POLICY_PROFILES.md`](docs/POLICY_PROFILES.md),
- an experiment workflow reference under [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md),
- a formal threat model under [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md),
- a feature taxonomy under [`docs/FEATURE_SCHEMA.md`](docs/FEATURE_SCHEMA.md),
- a named experiment preset config under [`configs/experiment_presets.json`](configs/experiment_presets.json),
- a named threshold-sweep preset config under [`configs/threshold_sweep_presets.json`](configs/threshold_sweep_presets.json),
- a baseline exposure scoring pipeline under [`src/signallock/exposure.py`](src/signallock/exposure.py),
- a baseline password-risk scoring pipeline under [`src/signallock/password_risk.py`](src/signallock/password_risk.py),
- a baseline hardening policy engine under [`src/signallock/policy.py`](src/signallock/policy.py),
- a template-based explanation renderer under [`src/signallock/explanation.py`](src/signallock/explanation.py),
- a synthetic evaluation harness under [`src/signallock/evaluation.py`](src/signallock/evaluation.py),
- a reproducible experiment reporting layer under [`src/signallock/reporting.py`](src/signallock/reporting.py),
- a cross-run analysis layer under [`src/signallock/analysis.py`](src/signallock/analysis.py),
- a pairwise comparison layer under [`src/signallock/comparison.py`](src/signallock/comparison.py),
- a lightweight SVG figure layer under [`src/signallock/figures.py`](src/signallock/figures.py),
- a preset-based orchestration layer under [`src/signallock/presets.py`](src/signallock/presets.py),
- a preset-results summary layer under [`src/signallock/results.py`](src/signallock/results.py),
- a paper-style preset aggregate layer under [`src/signallock/preset_aggregates.py`](src/signallock/preset_aggregates.py),
- a threshold-sweep experiment layer under [`src/signallock/threshold_sweeps.py`](src/signallock/threshold_sweeps.py),
- a cross-run threshold-sweep analysis layer under [`src/signallock/threshold_sweep_analysis.py`](src/signallock/threshold_sweep_analysis.py),
- a threshold-sweep figure layer under [`src/signallock/threshold_sweep_figures.py`](src/signallock/threshold_sweep_figures.py),
- a preset-driven multi-seed threshold-sweep orchestration layer under [`src/signallock/sweep_presets.py`](src/signallock/sweep_presets.py),
- a scikit-learn risk-band classifier under [`src/signallock/model.py`](src/signallock/model.py),
- an initial Python package scaffold under [`src/signallock/`](src/signallock/).

Repository:

- <https://github.com/sagarkishore-7/signallock>

## Research Framing

SignalLock is built around a dual-layer model:

- `Exposure Score`: estimates account targetability from consented or organization-approved public OSINT.
- `Password Risk Score`: estimates targeted password predictability conditioned on that exposure.
- `Hardening Recommendation`: maps the combined score to actions such as warn, step-up, enforce MFA, or prioritize awareness training.

This separation is deliberate. Public exposure is not the same thing as weak password choice, and the project treats them as distinct but related variables.

## Repository Structure

```text
SignalLock/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_POLICY.md
│   ├── EXPERIMENTS.md
│   ├── POLICY_PROFILES.md
│   ├── FEATURE_SCHEMA.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── THREAT_MODEL.md
├── configs/
│   ├── experiment_presets.json
│   ├── policy_profiles.json
│   └── threshold_sweep_presets.json
├── src/
│   └── signallock/
│       ├── __init__.py
│       ├── analysis.py
│       ├── cli.py
│       ├── comparison.py
│       ├── dataset.py
│       ├── evaluation.py
│       ├── explanation.py
│       ├── exposure.py
│       ├── figures.py
│       ├── model.py
│       ├── password_risk.py
│       ├── preset_aggregates.py
│       ├── policy.py
│       ├── presets.py
│       ├── reporting.py
│       ├── results.py
│       ├── schemas.py
│       ├── sweep_presets.py
│       ├── synthetic_profiles.py
│       ├── threshold_sweep_analysis.py
│       ├── threshold_sweep_figures.py
│       └── threshold_sweeps.py
├── tests/
│   ├── test_cli.py
│   ├── test_analysis.py
│   ├── test_comparison.py
│   ├── test_dataset.py
│   ├── test_evaluation.py
│   ├── test_explanation.py
│   ├── test_exposure.py
│   ├── test_figures.py
│   ├── test_model.py
│   ├── test_presets.py
│   ├── test_reporting.py
│   ├── test_results.py
│   ├── test_password_risk.py
│   ├── test_preset_aggregates.py
│   ├── test_policy.py
│   ├── test_schemas.py
│   ├── test_sweep_presets.py
│   ├── test_synthetic_profiles.py
│   ├── test_threshold_sweep_analysis.py
│   ├── test_threshold_sweep_figures.py
│   └── test_threshold_sweeps.py
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## Research Questions

SignalLock currently targets four core research questions:

1. Can public OSINT materially improve defensive prediction of targeted password risk beyond generic password meters?
2. Does separating exposure risk from password predictability produce better calibrated security decisions?
3. Can a combined model improve enterprise authentication hardening without excessive false positives?
4. Are OSINT-aware explanations more actionable than generic strength-meter feedback?

## Near-Term Milestones

### Phase 1

- finalize the threat model and ethics boundaries,
- define the structured OSINT feature schema,
- generate synthetic organizational profiles,
- establish baseline password-risk models.

### Phase 2

- implement the exposure engine, ✓
- implement the candidate-password risk engine, ✓
- add explainability and policy mapping, ✓
- build an analyst-facing dashboard and a local interactive mode.

### Phase 3

- evaluate calibration, false positives, and actionability,
- run controlled expert review and mock user studies,
- prepare a conference-style paper submission package.

## Safety and Ethics

SignalLock is intended strictly for defensive research and authorized enterprise security operations.

Non-goals:

- no generation of exploit-ready password dictionaries for real users,
- no targeting or profiling of specific individuals outside authorized contexts,
- no storage of real passwords in the proposed interactive mode,
- no scraping in violation of platform terms or organizational policy.

## Quick Start

This repository is in early implementation.

```bash
pip install -e .
signallock
```

Or, without installation:

```bash
PYTHONPATH=src python3 -m signallock
```

Generate sample synthetic profiles:

```bash
PYTHONPATH=src python3 -m signallock generate-profiles --count 3 --pretty
```

Generate baseline exposure assessments:

```bash
PYTHONPATH=src python3 -m signallock score-exposure --count 3 --pretty
```

Score a candidate password against a synthetic profile context:

```bash
PYTHONPATH=src python3 -m signallock score-password \
  --password "Priya2014!" \
  --seed 1 \
  --profile-index 0 \
  --pretty
```

Generate a hardening recommendation from both layers:

```bash
PYTHONPATH=src python3 -m signallock recommend-hardening \
  --password "Priya2014!" \
  --seed 1 \
  --profile-index 0 \
  --policy-profile balanced \
  --pretty
```

List the built-in policy profiles:

```bash
PYTHONPATH=src python3 -m signallock list-policy-profiles --pretty
```

Compare policy profiles across synthetic evaluation scenarios:

```bash
PYTHONPATH=src python3 -m signallock evaluate-policies \
  --count 5 \
  --seed 1 \
  --policy-profiles balanced strict usability \
  --include-table \
  --save-run \
  --pretty
```

That command now emits proxy calibration summaries as part of the evaluation output, including within-range agreement, under-hardening rate, over-hardening rate, and low-risk false-positive proxies.

Analyze multiple saved runs and export cross-run comparison artifacts:

```bash
PYTHONPATH=src python3 -m signallock analyze-runs \
  --input-dir artifacts/evaluations \
  --include-table \
  --save-analysis \
  --pretty
```

That analysis flow now carries both score summaries and calibration summaries across runs.

Generate aggregate SVG and CSV figures from saved runs:

```bash
PYTHONPATH=src python3 -m signallock generate-figures \
  --input-dir artifacts/evaluations \
  --include-aggregates \
  --include-table \
  --save-figures \
  --pretty
```

Compare a baseline policy directly against candidate policies across saved runs:

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

Produce a human-readable explanation of an exposure and password risk assessment:

```bash
PYTHONPATH=src python3 -m signallock explain-recommendation \
  --password "Priya2014!" \
  --seed 1 \
  --profile-index 0 \
  --policy-profile balanced \
  --pretty
```

The explanation output includes a per-sentence breakdown of each exposure and password risk factor, plus a full paragraph combining both layers into a coherent account of why the recommended action was chosen.

List available experiment presets:

```bash
PYTHONPATH=src python3 -m signallock list-experiment-presets --pretty
```

Execute a named preset end to end:

```bash
PYTHONPATH=src python3 -m signallock run-preset \
  --preset baseline_matrix \
  --pretty
```

Summarize executed preset bundles into thesis-friendly tables and CSV artifacts:

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

Those preset summaries now include per-policy calibration behavior aggregated across the evaluation runs inside each preset bundle.

Aggregate those preset summaries into paper-style cross-preset result tables:

```bash
PYTHONPATH=src python3 -m signallock aggregate-presets \
  --input-dir artifacts/presets \
  --include-tables \
  --save-aggregates \
  --pretty
```

That aggregate flow now includes cross-preset calibration tables alongside the existing score- and action-oriented summaries.

Run a threshold-sensitivity study without editing policy files:

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

The sweep output includes per-variant calibration metrics and deltas relative to the nearest-to-zero reference threshold profile, which makes it easier to see whether stricter or looser thresholds improve calibration or simply increase hardening pressure.

Aggregate saved threshold sweeps across runs:

```bash
PYTHONPATH=src python3 -m signallock analyze-threshold-sweeps \
  --input-dir artifacts/threshold_sweeps \
  --include-rows \
  --include-aggregates \
  --include-tables \
  --save-analysis \
  --pretty
```

Generate SVG figures from saved threshold sweeps:

```bash
PYTHONPATH=src python3 -m signallock generate-threshold-sweep-figures \
  --input-dir artifacts/threshold_sweeps \
  --include-aggregates \
  --include-table \
  --save-figures \
  --pretty
```

List available threshold-sweep presets:

```bash
PYTHONPATH=src python3 -m signallock list-sweep-presets --pretty
```

Execute a named threshold-sweep preset across multiple seeds and base profiles:

```bash
PYTHONPATH=src python3 -m signallock run-sweep-preset \
  --preset all_profiles_sweep \
  --pretty
```

Each sweep preset runs one threshold-sensitivity study per seed per base profile, then automatically aggregates and generates figures across the full set — producing a richer calibration picture than a single one-off sweep.

Train a scikit-learn risk-band classifier on a labeled dataset (requires `pip install signallock[ml]`):

```bash
# Generate training data first
PYTHONPATH=src python3 -m signallock generate-dataset \
  --count 50 --seed 1 --save-dataset

# Train from the saved CSV
PYTHONPATH=src python3 -m signallock train-model \
  --input-file artifacts/datasets/<timestamp>/dataset_records.csv \
  --model-type gradient_boosting \
  --save-model --pretty

# Or generate training data and train in one step
PYTHONPATH=src python3 -m signallock train-model \
  --count 50 --seed 1 \
  --model-type gradient_boosting \
  --save-model --pretty
```

The training output includes model accuracy, the heuristic baseline accuracy on the same test set, and the accuracy delta — the primary metric for the paper's model-versus-heuristic comparison.

Run the current test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Current Prototype Capabilities

- generate reproducible synthetic public profiles for experiments,
- normalize public profile data into attribute vectors,
- compute a transparent baseline exposure score,
- compute a transparent baseline password-risk score conditioned on profile context,
- compute a baseline hardening recommendation from both scores,
- produce human-readable per-factor explanations of exposure, password risk, and the recommended action,
- generate a labeled feature-matrix dataset for ML training and calibration analysis,
- train a scikit-learn gradient-boosted or logistic regression classifier on that dataset and compare it against the heuristic baseline,
- switch between named policy profiles for experiments,
- load policy thresholds from a repo-backed JSON config file,
- compare policy profiles across synthetic evaluation scenarios,
- measure proxy calibration behavior (within-range agreement, under- and over-hardening rates, TP/FP proxies),
- run threshold-sensitivity sweeps to study calibration without editing policy files,
- execute multi-seed, multi-profile threshold-sweep suites from named preset definitions,
- export timestamped evaluation artifact bundles with markdown comparison tables,
- aggregate saved runs into markdown and CSV comparison outputs,
- compare baseline and candidate policies with run-level deltas and action transitions,
- generate lightweight SVG charts and aggregate policy tables from saved runs,
- execute repeatable evaluation experiment suites from named preset definitions,
- summarize and aggregate preset bundles into thesis-friendly and paper-style tables,
- inspect outputs through a CLI-first workflow with test coverage.

## Current Limitations

- heuristic scoring is not yet replaced end-to-end by the trained classifier in the recommendation pipeline,
- calibration metrics are proxy measures over synthetic expectations, not real-world ground truth,
- password scoring currently operates on one synthetic profile context at a time,
- the policy engine is heuristic and not yet calibrated against user or org study data,
- policy profiles are loaded from JSON but still limited to the current named profile set,
- no dashboard has been added yet,
- comparisons operate on aggregate synthetic-run summaries rather than real deployment telemetry,
- preset execution orchestrates synthetic experiments only and does not yet capture notebook-style statistical post-processing,
- built-in figures are intentionally lightweight SVG outputs rather than full plotting-library workflows.

## Internal Planning Artifacts

Research proposal drafts and agent-only context files are intentionally kept out of the public repository.

## Implementation Roadmap

The engineering and research execution plan is documented in:

- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_POLICY.md`](docs/DATA_POLICY.md)
- [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md)
- [`docs/POLICY_PROFILES.md`](docs/POLICY_PROFILES.md)
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)
- [`docs/FEATURE_SCHEMA.md`](docs/FEATURE_SCHEMA.md)

## License

Apache-2.0
