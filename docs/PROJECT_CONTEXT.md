# Project Context

## Purpose

SignalLock is a research and prototype project at the intersection of:

- password security,
- OSINT,
- adaptive authentication,
- explainable risk scoring.

The goal is to produce a thesis-quality and paper-ready defensive system that helps organizations reason about password risk in a context-aware way without building offensive tooling.

## Why This Project Exists

Most password strength meters are context-free. They estimate guessability without considering whether publicly available user context makes a password more predictable to a targeted attacker.

At the same time, recent research shows that auxiliary data such as PII, email-derived attributes, and prior passwords can improve targeted guessing. The literature is much stronger on attack modeling than on defensive deployment. SignalLock exists to close that gap.

## Core Conceptual Decision

The most important design decision so far is this:

`public exposure` is not the same thing as `weak password choice`

That means the system should model at least two separate scores:

- `Exposure Score`
- `Password Predictability Score`

Then, and only then, should a policy layer combine them into actions such as:

- allow,
- warn,
- reject,
- require stronger password,
- enforce MFA,
- require step-up authentication,
- prioritize awareness training.

## Operating Modes

### 1. Audit Mode

Audience:

- enterprise security teams,
- researchers,
- authorized auditors.

Inputs:

- organization-approved roster,
- public-profile snapshots or other approved public records,
- policy settings.

Outputs:

- exposure heatmaps,
- per-user risk summaries,
- role- or department-level hardening recommendations.

### 2. Interactive Mode

Audience:

- end users during password creation or password change,
- security teams testing password-policy options.

Inputs:

- candidate password,
- local or organization-approved attribute vector,
- policy settings.

Outputs:

- candidate-password risk score,
- explanation,
- security action or recommendation.

## Research Claims the Project Should Make

The project should claim:

- it estimates targeted password risk defensively,
- it uses ethical OSINT-derived context,
- it supports authentication hardening,
- it provides explainable and calibrated outputs.

The project should avoid claiming:

- that it predicts a user's real password directly,
- that exposure alone proves password weakness,
- that it can safely use arbitrary live-profile scraping without strict governance.

## Ethical Data Strategy

Preferred sources:

- synthetic personas,
- synthetic organization rosters,
- synthetic public-profile text,
- aggregate statistics from public password corpora,
- consent-based mock-account studies,
- organization-approved profile snapshots for controlled testing.

Avoid:

- unauthorized profiling of real individuals,
- live scraping that may violate terms or expectations,
- storing real plaintext passwords,
- re-identification from leaked credential pairs.

## Current Technical Direction

### Language and Runtime

- Python 3.11+

### Likely Libraries

- `pydantic` for schemas
- `spaCy` for profile-text extraction
- `pandas` / `numpy` for data handling
- `scikit-learn` and possibly `xgboost` or `lightgbm` for initial models
- `FastAPI` for service layer
- `React` for later dashboard work

### Initial Modules to Build

- `schemas/` or equivalent data models
- synthetic profile generator
- exposure feature extractor
- candidate-password feature extractor
- risk scoring engine
- policy engine
- explanation layer

## Current Repository Contents

- `README.md`
  High-level project framing and repo overview

- `docs/IMPLEMENTATION_PLAN.md`
  Detailed engineering roadmap

- `proposal/main.tex`
  Main research proposal draft in LaTeX

- `src/signallock/`
  Minimal Python package scaffold and placeholder CLI

## Immediate Implementation Priorities

1. Threat model
2. Feature schema
3. Synthetic data generator
4. Baseline exposure engine
5. Baseline candidate-password risk engine
6. Evaluation harness

## Open Design Questions

- What exact online-guess budgets should define low/medium/high targeted risk?
- How much of the exposure engine should rely on free text versus structured inputs?
- Should the first model be purely tabular for interpretability or include a neural baseline from the start?
- What is the smallest meaningful dashboard MVP versus a CLI-only first milestone?
- How should organization-specific conventions such as email formats be represented in the schema?

## Suggested Reading Order for New Work

1. `README.md`
2. `docs/IMPLEMENTATION_PLAN.md`
3. `proposal/main.tex`
4. `docs/HANDOFF.md`

Then begin implementation from threat model and schemas rather than jumping straight into model training.
