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
- support multiple named policy profiles for experiments.

### `src/signallock/cli.py`

Responsibilities:

- expose prototype workflows through a simple CLI,
- generate synthetic profiles,
- score exposure,
- score candidate passwords against synthetic profile context.

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

## Near-Term Architecture Expansion

The next likely modules are:

- policy engine,
- explanation renderer,
- password feature calibration support,
- dataset generation for controlled evaluation,
- experiment harness.

## CLI-Oriented Workflow

Today the repository is CLI-first. A typical prototype loop is:

1. Generate synthetic profiles.
2. Score exposure for those profiles.
3. Score a candidate password against one profile context.
4. Apply a named hardening policy profile.
5. Inspect component-level results and refine the scoring logic.

That keeps the implementation transparent and testable before introducing more complex modeling.
