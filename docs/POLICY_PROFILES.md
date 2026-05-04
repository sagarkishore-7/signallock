# SignalLock Policy Profiles

## Purpose

SignalLock uses named policy profiles to convert exposure and password-risk scores into hardening actions without hard-coding one operating point for every experiment.

The current prototype ships with three built-in profiles:

- `balanced`
- `strict`
- `usability`

## Profile Summary

### `balanced`

Intended use:

- default research demonstrations,
- moderate sensitivity,
- reasonable trade-off between security friction and risk response.

Behavior:

- moderate warn threshold,
- step-up and MFA triggered at mid-to-high combined risk,
- stronger-password enforcement reserved for clearly high contextual risk.

### `strict`

Intended use:

- high-risk environments,
- leadership accounts,
- more conservative security postures.

Behavior:

- lower warn threshold,
- more aggressive step-up and MFA support,
- stronger-password enforcement triggered earlier.

### `usability`

Intended use:

- lower-friction environments,
- early pilots,
- demos where alert fatigue should be minimized.

Behavior:

- higher warn threshold,
- fewer exposure-only escalations,
- stronger-password enforcement reserved for the most obvious contextual risk.

## Current Dimensions

Each profile currently defines:

- exposure weight
- password weight
- warn threshold
- step-up threshold
- MFA threshold
- minimum exposure band for awareness training
- minimum exposure band for step-up
- minimum exposure band for MFA
- minimum password band for immediate stronger-password enforcement
- paired exposure/password thresholds for stronger-password enforcement

## CLI Usage

List available profiles:

```bash
PYTHONPATH=src python3 -m signallock list-policy-profiles --pretty
```

The default profile definitions live in:

`configs/policy_profiles.json`

Use a different file for experiments:

```bash
PYTHONPATH=src python3 -m signallock list-policy-profiles \
  --policy-file /path/to/policies.json \
  --pretty
```

Apply a profile:

```bash
PYTHONPATH=src python3 -m signallock recommend-hardening \
  --password "Priya2014!" \
  --seed 1 \
  --profile-index 0 \
  --policy-file configs/policy_profiles.json \
  --policy-profile strict \
  --pretty
```

Evaluate multiple profiles at once:

```bash
PYTHONPATH=src python3 -m signallock evaluate-policies \
  --count 5 \
  --seed 1 \
  --policy-profiles balanced strict usability \
  --pretty
```

## Current Limitation

These profiles are heuristic baselines, not empirically calibrated organizational policies. Their main purpose today is to support comparative experiments and make the prototype easier to evolve. The repository now includes a synthetic evaluation harness so these profiles can be compared without changing code.
