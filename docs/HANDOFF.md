# Handoff Notes

## What Was Decided

- The project name was changed from `Brainstorm` to `SignalLock`.
- The repository was created and pushed to GitHub:
  `https://github.com/sagarkishore-7/signallock`
- The core merged concept combines:
  - enterprise-facing exposure scoring,
  - privacy-conscious candidate-password risk scoring,
  - context-aware authentication hardening.
- The key methodological correction is to keep exposure risk and password predictability risk separate until the policy layer.

## Files Created During Initial Setup

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `.github/pull_request_template.md`
- `proposal/main.tex`
- `proposal/references.bib`
- `docs/IMPLEMENTATION_PLAN.md`
- Python package scaffold in `src/signallock/`

## What Has Been Verified

- Local git repository initialized
- Initial commits created and pushed
- Placeholder CLI works with:

```bash
PYTHONPATH=src python3 -m signallock
```

- Citation keys in the LaTeX proposal were checked for consistency

## Known Environment Constraints

- `pdflatex` was not installed during initial setup, so the proposal PDF was not generated in this environment

## Recommended Next Tasks

1. Create `docs/THREAT_MODEL.md`
2. Create `docs/FEATURE_SCHEMA.md`
3. Add `src/signallock/schemas.py`
4. Add `src/signallock/synthetic_profiles.py`
5. Add a basic CLI command for generating synthetic profiles
6. Add tests for schema validation and sample data generation

## Short Implementation Order

### First

- threat model,
- feature schema,
- synthetic data generation.

### Next

- exposure scoring,
- candidate-password scoring,
- calibration,
- policy mapping.

### Then

- explanations,
- CLI workflows,
- dashboard/API,
- experiment harness and reporting.

## Guiding Principle

If a future implementation choice makes the tool better at offensive targeting than at defensive measurement or authentication hardening, redesign it before proceeding.
