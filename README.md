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

This repository is in the research and design stage.

Current contents:

- a detailed implementation roadmap under [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md),
- a formal threat model under [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md),
- a feature taxonomy under [`docs/FEATURE_SCHEMA.md`](docs/FEATURE_SCHEMA.md),
- an initial Python package scaffold under [`src/signallock/`](src/signallock/).

Repository:

- <https://github.com/sagarkishore-7/signallock>

## Research Framing

SignalLock is built around a dual-layer model:

- `Exposure Score`: estimates account targetability from consented or organization-approved public OSINT.
- `Password Risk Score`: estimates targeted password predictability conditioned on that exposure.
- `Hardening Recommendation`: maps the combined score to actions such as warn, step-up, enforce MFA, or prioritize awareness training.

This separation is deliberate. Public exposure is not the same thing as weak password choice, and the project treats them as distinct but related variables.

## Planned Repository Structure

```text
SignalLock/
├── docs/
│   ├── FEATURE_SCHEMA.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── THREAT_MODEL.md
├── src/
│   └── signallock/
│       ├── __init__.py
│       ├── cli.py
│       ├── schemas.py
│       └── synthetic_profiles.py
├── tests/
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

## Internal Planning Artifacts

Research proposal drafts and agent-only context files are intentionally kept out of the public repository.

## Implementation Roadmap

The engineering and research execution plan is documented in:

- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)
- [`docs/FEATURE_SCHEMA.md`](docs/FEATURE_SCHEMA.md)

## License

Apache-2.0
