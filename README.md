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
- a baseline exposure scoring pipeline under [`src/signallock/exposure.py`](src/signallock/exposure.py),
- a baseline password-risk scoring pipeline under [`src/signallock/password_risk.py`](src/signallock/password_risk.py),
- a baseline hardening policy engine under [`src/signallock/policy.py`](src/signallock/policy.py),
- a synthetic evaluation harness under [`src/signallock/evaluation.py`](src/signallock/evaluation.py),
- a reproducible experiment reporting layer under [`src/signallock/reporting.py`](src/signallock/reporting.py),
- a cross-run analysis layer under [`src/signallock/analysis.py`](src/signallock/analysis.py),
- a pairwise comparison layer under [`src/signallock/comparison.py`](src/signallock/comparison.py),
- a lightweight SVG figure layer under [`src/signallock/figures.py`](src/signallock/figures.py),
- a preset-based orchestration layer under [`src/signallock/presets.py`](src/signallock/presets.py),
- a preset-results summary layer under [`src/signallock/results.py`](src/signallock/results.py),
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
│   └── policy_profiles.json
├── src/
│   └── signallock/
│       ├── __init__.py
│       ├── analysis.py
│       ├── cli.py
│       ├── comparison.py
│       ├── evaluation.py
│       ├── exposure.py
│       ├── figures.py
│       ├── password_risk.py
│       ├── policy.py
│       ├── presets.py
│       ├── reporting.py
│       ├── results.py
│       ├── schemas.py
│       └── synthetic_profiles.py
├── tests/
│   ├── test_cli.py
│   ├── test_analysis.py
│   ├── test_comparison.py
│   ├── test_evaluation.py
│   ├── test_exposure.py
│   ├── test_figures.py
│   ├── test_presets.py
│   ├── test_reporting.py
│   ├── test_results.py
│   ├── test_password_risk.py
│   ├── test_policy.py
│   ├── test_schemas.py
│   └── test_synthetic_profiles.py
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

- implement the exposure engine,
- implement the candidate-password risk engine,
- add explainability and policy mapping,
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

Analyze multiple saved runs and export cross-run comparison artifacts:

```bash
PYTHONPATH=src python3 -m signallock analyze-runs \
  --input-dir artifacts/evaluations \
  --include-table \
  --save-analysis \
  --pretty
```

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
- switch between named policy profiles for experiments,
- load policy thresholds from a repo-backed JSON config file,
- compare policy profiles across synthetic evaluation scenarios,
- export timestamped evaluation artifact bundles with markdown comparison tables,
- aggregate saved runs into markdown and CSV comparison outputs,
- compare baseline and candidate policies with run-level deltas and action transitions,
- generate lightweight SVG charts and aggregate policy tables from saved runs,
- execute repeatable experiment suites from named preset definitions,
- inspect outputs through a CLI-first workflow with test coverage.

## Current Limitations

- scoring is heuristic and not yet calibrated against empirical study data,
- no ML models are in the loop yet,
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
