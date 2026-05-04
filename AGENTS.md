# SignalLock Agent Notes

This repository is a defensive cybersecurity research project. Future work should treat it as a dual-use-sensitive codebase and preserve the current defensive framing.

## Project Identity

- Tool name: `SignalLock`
- Repo: `https://github.com/sagarkishore-7/signallock`
- Main problem area: OSINT-calibrated password risk assessment and context-aware enterprise authentication hardening

## Core Research Position

The central idea is to keep two variables separate:

1. `Exposure Risk`
   How publicly visible and targetable an account is based on organization-approved or consented OSINT.

2. `Password Predictability Risk`
   How risky a candidate password is when conditioned on that exposure.

These should only be combined at the policy layer. Do not collapse them into a single undifferentiated "password risk" score too early.

## Intended Product Modes

### Audit Mode

Used by authorized enterprise security teams to:

- rank public exposure,
- prioritize MFA and awareness interventions,
- produce explainable per-user risk summaries.

### Interactive Mode

Used during password creation or password change to:

- evaluate a candidate password locally or in a privacy-conscious way,
- explain why it is risky under the user's public context,
- recommend actions such as accept, warn, reject, or require MFA.

## Hard Safety Boundaries

- No exploit-ready password generation for real users.
- No profiling of unauthorized real individuals.
- No scraping or collection that violates platform terms or organizational policy.
- Prefer synthetic, anonymized, or consent-based data.
- No storage of real plaintext passwords in the intended interactive workflow.

## Current Repository State

- Research proposal drafted in `proposal/main.tex`
- Implementation roadmap drafted in `docs/IMPLEMENTATION_PLAN.md`
- Minimal Python scaffold in `src/signallock/`
- Local git repo initialized and pushed to GitHub

## Best Next Steps

1. Write `docs/THREAT_MODEL.md`
2. Write `docs/FEATURE_SCHEMA.md`
3. Scaffold synthetic profile generation
4. Scaffold candidate-password feature extraction
5. Add first CLI workflows for synthetic evaluation

## Important Documents

- `README.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `proposal/main.tex`
- `docs/PROJECT_CONTEXT.md`
- `docs/HANDOFF.md`

## Environment Notes

- The repo is under `/Users/sagarkishore/Cysec Tools/SignalLock`
- `pdflatex` was not available during initial setup, so the LaTeX proposal was not compiled here
- The placeholder CLI works with:

```bash
PYTHONPATH=src python3 -m signallock
```
