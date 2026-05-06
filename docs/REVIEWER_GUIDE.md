# SignalLock Reviewer Guide

This guide is meant to accompany a completed review packet such as
`review_tasks_balanced_seed1_ml.csv`.

## Purpose

You are being asked to review synthetic password-risk scenarios for a defensive
cybersecurity research project. The goal is to compare:

- a heuristic password-risk assessment,
- an ML-assisted password-risk assessment,
- and expert human judgement.

These scenarios are synthetic and are not tied to real unauthorized users.

## What You Will See

Each row describes one task:

- a synthetic public-profile summary,
- a candidate password,
- empty fields for your rating.

Depending on the study packet, you may also see reference columns such as:

- `heuristic_band`
- `heuristic_action`
- `ml_predicted_band`

If those columns are present, please treat them as system metadata rather than
as instructions for your answer.

In some study packets, these fields may be intentionally blank. That is normal
for blind-review mode and is intended to reduce anchoring bias.

## What To Fill In

Please edit only:

- `expert_band`
- `expert_action`
- `notes`

Do not modify:

- `task_id`
- `profile_id`
- `scenario_name`
- `profile_summary`
- `password`
- any system-generated reference columns

## Rating Frame

Rate each password as if you were assessing **targeted online risk** under a
bounded guess budget, not offline cracking resistance.

Use these labels:

- `LOW`: unlikely to be reached in a low-budget targeted online attack.
- `MEDIUM`: some contextual relevance, but limited structural predictability.
- `HIGH`: realistically reachable in a targeted online campaign.
- `CRITICAL`: strongly context-derived or highly predictable; should trigger
  strong hardening or rejection.

## Optional Action Rating

If you want to suggest a hardening action, use one of:

- `ALLOW`
- `WARN`
- `REQUIRE_STRONGER_PASSWORD`
- `ENFORCE_MFA`
- `STEP_UP_AUTHENTICATION`
- `PRIORITIZE_AWARENESS_TRAINING`

If you are unsure, leave `expert_action` blank. The band rating is the primary
study signal.

## Notes

Use `notes` to explain:

- why a rating differs from the system output,
- which public-context cues mattered most,
- whether a case feels ambiguous,
- or whether the available context is insufficient.

These notes are especially valuable for disagreement analysis later.

## Return Format

Please return the completed CSV with the same column structure and encoding.
Do not reorder or rename columns.
