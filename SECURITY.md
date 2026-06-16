# Security Policy

## Scope

Eidolon is a defensive cybersecurity research project focused on:

- OSINT-calibrated risk assessment,
- password security research,
- adaptive authentication hardening,
- explainable defensive tooling.

The repository is intentionally designed to avoid exploit-ready offensive workflows.

## Supported Versions

At this stage, only the latest `main` branch is considered supported.

## Reporting a Security Issue

If you discover a security issue in the code, documentation, or planned design:

1. Do not open a public issue if the report could increase misuse risk.
2. Share a private report with enough detail to reproduce the issue responsibly.
3. Clearly identify whether the issue affects:
   - data handling,
   - access control,
   - privacy leakage,
   - unsafe offensive dual-use behavior,
   - or model output misuse risk.

## Responsible Research Expectations

Reports are especially valuable when they identify:

- ways the system could expose sensitive profile data,
- ways explanations could leak more than intended,
- ways scoring outputs could be repurposed for offensive profiling,
- or places where the implementation drifts from the project's defensive-only scope.
