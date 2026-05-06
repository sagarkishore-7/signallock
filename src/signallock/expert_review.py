"""Empirical calibration infrastructure: expert review task generation and ingestion.

This module makes a controlled user study tractable. The workflow is:

1. ``generate_review_tasks(profiles, ...)`` produces a list of
   ``ExpertReviewTask`` instances — one per (profile, scenario) pair —
   each containing a human-readable profile summary, the candidate
   password, and the heuristic/ML reference bands. Save the tasks as a
   spreadsheet-friendly CSV with ``write_review_tasks_csv``.

2. Send the CSV to security experts. Each expert fills in
   ``expert_band`` (LOW, MEDIUM, HIGH, CRITICAL), optionally
   ``expert_action``, and free-form ``notes``.

3. ``import_expert_ratings_csv`` reads the completed CSV back in.

4. ``compute_external_calibration`` cross-references the ratings with
   the dataset records (which carry the heuristic and optional ML
   bands) and returns three-way agreement metrics.

The ``expected_risk_band`` from ``SyntheticScenarioSpec`` is not used
here — expert ratings are the ground truth, the synthetic labels are
the proxy this layer is designed to validate or replace.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .evaluation import generate_synthetic_scenario_specs
from .exposure import score_exposure
from .password_risk import score_password_for_profile
from .policy import get_policy_config, recommend_hardening
from .schemas import (
    DatasetRecord,
    ExpertRating,
    ExpertReviewTask,
    ExternalCalibrationResult,
    HardeningAction,
    PolicyProfile,
    PublicProfile,
    RiskBand,
)


_BAND_RANK = {
    RiskBand.LOW: 0,
    RiskBand.MEDIUM: 1,
    RiskBand.HIGH: 2,
    RiskBand.CRITICAL: 3,
}

_REVIEW_TASK_FIELDNAMES = [
    "task_id",
    "profile_id",
    "scenario_name",
    "profile_summary",
    "password",
    "heuristic_band",
    "heuristic_action",
    "ml_predicted_band",
    "expert_band",
    "expert_action",
    "notes",
]


def _profile_summary(profile: PublicProfile) -> str:
    """Compact one-line description suitable for an expert reviewer."""
    seniority = profile.role_seniority.value.replace("_", " ").lower()
    platforms = ", ".join(p.value for p in profile.platforms) or "no public platforms"
    interests = ", ".join(profile.interests[:2]) if profile.interests else "no listed interests"
    username = profile.public_usernames[0] if profile.public_usernames else "no public username"
    return (
        f"{profile.full_name} — {profile.title} ({seniority}) at {profile.organization} — "
        f"{profile.location} — joined {profile.tenure_start_year} — "
        f"{profile.platform_count} public platform(s): {platforms} — "
        f"username '{username}' — interests: {interests}"
    )


def generate_review_tasks(
    profiles: list[PublicProfile],
    policy_profile: PolicyProfile = PolicyProfile.BALANCED,
    policy_file: str | Path | None = None,
) -> list[ExpertReviewTask]:
    """Build one review task per (profile, scenario) pair.

    Each task carries a profile summary, the candidate password, and the
    heuristic band/action. The ``ml_predicted_band`` field is left blank
    here — the caller may fill it in if they want experts to see the ML
    output as well (typically you want experts to rate without seeing it).
    """
    config = get_policy_config(policy_profile, policy_file=policy_file)
    tasks: list[ExpertReviewTask] = []
    counter = 0

    for profile in profiles:
        exposure = score_exposure(profile)
        summary = _profile_summary(profile)
        for spec in generate_synthetic_scenario_specs(profile):
            password_assessment = score_password_for_profile(spec.password, profile)
            recommendation = recommend_hardening(
                exposure, password_assessment, config=config
            )
            counter += 1
            tasks.append(
                ExpertReviewTask(
                    task_id=f"T{counter:04d}",
                    profile_id=profile.employee_id,
                    scenario_name=spec.name,
                    profile_summary=summary,
                    password=spec.password,
                    heuristic_band=password_assessment.band,
                    heuristic_action=recommendation.primary_action,
                )
            )
    return tasks


def write_review_tasks_csv(tasks: list[ExpertReviewTask]) -> str:
    """Render review tasks as a Excel-friendly CSV with empty rating columns."""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_REVIEW_TASK_FIELDNAMES)
    writer.writeheader()
    for task in tasks:
        writer.writerow(task.to_dict())
    return buffer.getvalue()


def write_review_tasks_json(tasks: list[ExpertReviewTask], pretty: bool = False) -> str:
    """Render review tasks as JSON for programmatic use."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_count": len(tasks),
        "tasks": [task.to_dict() for task in tasks],
    }
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def import_expert_ratings_csv(csv_path: str | Path) -> list[ExpertRating]:
    """Read a completed review CSV back into typed ``ExpertRating`` instances.

    Rows with empty ``expert_band`` are skipped silently — partially completed
    CSVs are valid input.
    """
    path = Path(csv_path)
    ratings: list[ExpertRating] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            band_str = (row.get("expert_band") or "").strip().upper()
            if not band_str:
                continue
            try:
                expert_band = RiskBand(band_str)
            except ValueError:
                raise ValueError(
                    f"row task_id={row.get('task_id')!r} has invalid expert_band {band_str!r}"
                )
            action_str = (row.get("expert_action") or "").strip().upper()
            expert_action: HardeningAction | None = None
            if action_str:
                try:
                    expert_action = HardeningAction(action_str)
                except ValueError:
                    raise ValueError(
                        f"row task_id={row.get('task_id')!r} has invalid expert_action {action_str!r}"
                    )
            ratings.append(
                ExpertRating(
                    task_id=str(row.get("task_id", "")).strip(),
                    profile_id=str(row.get("profile_id", "")).strip(),
                    scenario_name=str(row.get("scenario_name", "")).strip(),
                    expert_band=expert_band,
                    expert_action=expert_action,
                    notes=str(row.get("notes", "")).strip(),
                )
            )
    return ratings


def compute_external_calibration(
    records: list[DatasetRecord],
    ratings: list[ExpertRating],
    ml_predicted_bands: dict[str, RiskBand] | None = None,
) -> ExternalCalibrationResult:
    """Compare heuristic (and optional ML) bands to expert ratings.

    Args:
        records: dataset records carrying the heuristic ``password_band``.
        ratings: expert ratings keyed by ``(profile_id, scenario_name)``.
        ml_predicted_bands: optional mapping ``(profile_id, scenario_name)`` →
            ``RiskBand`` representing ML predictions for the same pairs.

    Returns:
        ExternalCalibrationResult with match rates, distributions, and a
        list of disagreement details for the paper's qualitative section.
    """
    rating_index = {(r.profile_id, r.scenario_name): r for r in ratings}
    record_index = {(r.employee_id, r.scenario_name): r for r in records}

    matched_keys = [k for k in rating_index if k in record_index]
    if not matched_keys:
        raise ValueError("no overlap between ratings and records — check task_ids and scenario names")

    heuristic_matches = 0
    ml_matches = 0
    ml_total = 0
    heuristic_ml_matches = 0
    heuristic_ml_total = 0
    severe = 0
    expert_dist: dict[str, int] = {}
    heuristic_dist: dict[str, int] = {}
    ml_dist: dict[str, int] = {}
    transitions: dict[str, int] = {}
    disagreements: list[dict[str, object]] = []

    for key in matched_keys:
        rating = rating_index[key]
        record = record_index[key]
        expert_band = rating.expert_band
        heuristic_band = record.password_band

        expert_dist[expert_band.value] = expert_dist.get(expert_band.value, 0) + 1
        heuristic_dist[heuristic_band.value] = heuristic_dist.get(heuristic_band.value, 0) + 1

        if heuristic_band == expert_band:
            heuristic_matches += 1
        else:
            transition = f"{heuristic_band.value}→{expert_band.value}"
            transitions[transition] = transitions.get(transition, 0) + 1
            distance = abs(_BAND_RANK[heuristic_band] - _BAND_RANK[expert_band])
            if distance >= 2:
                severe += 1
            disagreements.append(
                {
                    "task_id": rating.task_id,
                    "profile_id": rating.profile_id,
                    "scenario_name": rating.scenario_name,
                    "heuristic_band": heuristic_band.value,
                    "expert_band": expert_band.value,
                    "distance": distance,
                    "notes": rating.notes,
                }
            )

        if ml_predicted_bands is not None and key in ml_predicted_bands:
            ml_band = ml_predicted_bands[key]
            ml_dist[ml_band.value] = ml_dist.get(ml_band.value, 0) + 1
            ml_total += 1
            if ml_band == expert_band:
                ml_matches += 1
            heuristic_ml_total += 1
            if heuristic_band == ml_band:
                heuristic_ml_matches += 1

    rating_count = len(matched_keys)
    return ExternalCalibrationResult(
        rating_count=rating_count,
        heuristic_vs_expert_match_rate=round(heuristic_matches / rating_count, 4),
        ml_vs_expert_match_rate=(
            round(ml_matches / ml_total, 4) if ml_total else None
        ),
        heuristic_vs_ml_match_rate=(
            round(heuristic_ml_matches / heuristic_ml_total, 4)
            if heuristic_ml_total
            else None
        ),
        severe_disagreement_count=severe,
        expert_band_distribution=expert_dist,
        heuristic_band_distribution=heuristic_dist,
        ml_band_distribution=ml_dist if ml_total else None,
        band_transition_counts=transitions,
        disagreement_details=disagreements,
    )


def calibration_result_to_json(
    result: ExternalCalibrationResult,
    pretty: bool = False,
) -> str:
    """Serialize an external calibration result as JSON."""
    payload = result.to_dict()
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
