# SignalLock Expert Review Protocol

This document describes the recommended workflow for collecting expert ratings
for SignalLock's external calibration step.

## Goal

Move from proxy-only synthetic calibration to a three-way comparison:

- heuristic band vs expert judgement
- ML-predicted band vs expert judgement
- heuristic band vs ML-predicted band

## Recommended Workflow

### 1. Generate the labeled dataset used for calibration

```bash
.venv/bin/python -m signallock generate-dataset \
  --count 100 \
  --seed 1 \
  --policy-profile balanced \
  --save-dataset \
  --output-dir artifacts/datasets \
  --pretty
```

Keep the resulting `dataset_records.csv`. This is the structured reference used
later by `compute-external-calibration`.

### 2. Train and save the ML model you want to compare

```bash
.venv/bin/python -m signallock train-model \
  --input-file artifacts/datasets/<timestamp>/dataset_records.csv \
  --model-type gradient_boosting \
  --save-model \
  --output-dir artifacts/models \
  --pretty
```

Keep the saved `.pkl` and `model_metadata.json` together.

### 3. Generate expert review packets

If you want the review packet to support three-way comparison, generate it with
the same saved model:

```bash
.venv/bin/python -m signallock generate-review-tasks \
  --count 10 \
  --seed 1 \
  --policy-profile balanced \
  --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl \
  --format csv \
  --output-file artifacts/review_tasks/review_tasks_balanced_seed1.csv
```

This fills the `ml_predicted_band` column in the CSV.

Also export JSON if you want a programmatic copy:

```bash
.venv/bin/python -m signallock generate-review-tasks \
  --count 10 \
  --seed 1 \
  --policy-profile balanced \
  --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl \
  --format json \
  --output-file artifacts/review_tasks/review_tasks_balanced_seed1.json
```

### 4. Send the CSV to expert reviewers

Use these companion docs when sending the packet:

- [`docs/REVIEWER_GUIDE.md`](REVIEWER_GUIDE.md)
- [`docs/REVIEWER_INVITE_TEMPLATE.md`](REVIEWER_INVITE_TEMPLATE.md)

Reviewers should fill in:

- `expert_band`
- `expert_action` (optional)
- `notes` (optional but encouraged)

They should not modify:

- `task_id`
- `profile_id`
- `scenario_name`
- `heuristic_band`
- `heuristic_action`
- `ml_predicted_band`

## Reviewer Guidance

Ask reviewers to rate each candidate password as if they were assessing
targeted online risk under bounded guess budgets, not offline cracking
resistance.

Suggested interpretation:

- `LOW`: unlikely to fall in a low-budget targeted online attack window
- `MEDIUM`: some public-context overlap, but limited structural predictability
- `HIGH`: likely reachable in a realistic targeted online campaign
- `CRITICAL`: strong contextual overlap, likely requiring rejection or mandatory hardening

## Compute External Calibration

After reviewers complete the CSV:

```bash
.venv/bin/python -m signallock compute-external-calibration \
  --records-file artifacts/datasets/<timestamp>/dataset_records.csv \
  --ratings-file artifacts/review_tasks/review_tasks_balanced_seed1_completed.csv \
  --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl \
  --pretty
```

Important:

- `compute-external-calibration` now expects ML comparisons to come from the
  `ml_predicted_band` values already embedded in the review CSV.
- If the completed CSV does not contain `ml_predicted_band`, you will still get
  heuristic-vs-expert calibration, but not ML-vs-expert calibration.
- If you pass `--model-file` but the CSV has no `ml_predicted_band` values, the
  command will stop and tell you to regenerate the packet with
  `generate-review-tasks --model-file`.

## Summarize Multiple Reviewers

After you receive multiple completed CSVs, aggregate them into one
reviewer-summary bundle:

```bash
.venv/bin/python -m signallock summarize-expert-reviews \
  --records-file artifacts/datasets/<timestamp>/dataset_records.csv \
  --ratings-files \
    artifacts/review_tasks/reviewer_a_completed.csv \
    artifacts/review_tasks/reviewer_b_completed.csv \
    artifacts/review_tasks/reviewer_c_completed.csv \
  --model-file artifacts/models/<timestamp>/model_gradient_boosting.pkl \
  --include-reviewer-summaries \
  --include-consensus-tasks \
  --include-table \
  --save-summary \
  --pretty
```

This produces:

- one calibration summary per reviewer,
- mean agreement metrics across reviewers,
- a consensus task summary,
- and a consensus calibration result against the dataset records.

## Suggested Study Design

- Start with `N=3` to `N=5` security practitioners for a pilot.
- Use one fixed synthetic batch first, then expand to multiple seeds.
- Keep the candidate set balanced across `LOW`, `MEDIUM`, `HIGH`, and
  `CRITICAL` synthetic labels.
- Capture reviewer notes for qualitative disagreement analysis.

## Deliverables to Preserve

- completed reviewer CSVs
- original generated review packet CSV/JSON
- the matching `dataset_records.csv`
- the exact saved model artifact used to generate `ml_predicted_band`
- the resulting calibration JSON

Together, these provide a reproducible chain from scenario generation to
expert-grounded calibration analysis.
