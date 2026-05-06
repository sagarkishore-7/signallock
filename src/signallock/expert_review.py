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
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import StringIO
from itertools import combinations
from pathlib import Path

from .analysis import _create_unique_run_directory
from .evaluation import generate_synthetic_scenario_specs
from .exposure import profile_to_attribute_vector
from .exposure import score_exposure
from .model import load_model_artifacts, predict_risk_band
from .password_risk import score_password_for_profile
from .paths import artifacts_path
from .policy import get_policy_config, recommend_hardening
from .reporting import normalize_artifact_path
from .schemas import (
    ConsensusTaskSummary,
    DatasetRecord,
    ExpertReviewArtifacts,
    ExpertReviewBatchSummary,
    ExpertRating,
    ExpertReviewTask,
    ExternalCalibrationResult,
    HardeningAction,
    PolicyProfile,
    PublicProfile,
    RiskBand,
    ReviewerCalibrationSummary,
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

DEFAULT_EXPERT_REVIEW_OUTPUT_DIR = artifacts_path("expert_review")


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
    model_file: str | Path | None = None,
) -> list[ExpertReviewTask]:
    """Build one review task per (profile, scenario) pair.

    Each task carries a profile summary, the candidate password, and the
    heuristic band/action. When ``model_file`` is supplied, the task also
    carries an ``ml_predicted_band`` generated from the saved model so the
    review packet can support three-way comparison (heuristic vs ML vs expert).
    """
    config = get_policy_config(policy_profile, policy_file=policy_file)
    fitted_model = None
    if model_file is not None:
        fitted_model, _ = load_model_artifacts(model_file)
    tasks: list[ExpertReviewTask] = []
    counter = 0

    for profile in profiles:
        exposure = score_exposure(profile)
        summary = _profile_summary(profile)
        vector = profile_to_attribute_vector(profile)
        for spec in generate_synthetic_scenario_specs(profile):
            password_assessment = score_password_for_profile(spec.password, profile)
            recommendation = recommend_hardening(
                exposure, password_assessment, config=config
            )
            ml_predicted_band = None
            if fitted_model is not None:
                ml_predicted_band = predict_risk_band(
                    fitted_model,
                    vector,
                    password_assessment,
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
                    ml_predicted_band=ml_predicted_band,
                )
            )
    return tasks


def _review_task_row(
    task: ExpertReviewTask,
    *,
    include_references: bool,
) -> dict[str, object]:
    """Convert a review task into an export row, optionally hiding reference bands."""
    row = task.to_dict()
    if not include_references:
        row["heuristic_band"] = ""
        row["heuristic_action"] = ""
        row["ml_predicted_band"] = ""
    return row


def write_review_tasks_csv(
    tasks: list[ExpertReviewTask],
    *,
    include_references: bool = True,
) -> str:
    """Render review tasks as an Excel-friendly CSV with empty rating columns."""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_REVIEW_TASK_FIELDNAMES)
    writer.writeheader()
    for task in tasks:
        writer.writerow(_review_task_row(task, include_references=include_references))
    return buffer.getvalue()


def write_review_tasks_json(
    tasks: list[ExpertReviewTask],
    pretty: bool = False,
    *,
    include_references: bool = True,
) -> str:
    """Render review tasks as JSON for programmatic use."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_count": len(tasks),
        "tasks": [
            _review_task_row(task, include_references=include_references) for task in tasks
        ],
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


def extract_ml_predicted_bands_csv(
    csv_path: str | Path,
) -> dict[tuple[str, str], RiskBand]:
    """Read ML reference bands embedded in a review CSV.

    The generated review packet keeps ``ml_predicted_band`` alongside the task,
    which is a safer provenance path than trying to reconstruct predictions
    later from incomplete dataset rows alone.
    """
    path = Path(csv_path)
    ml_bands: dict[tuple[str, str], RiskBand] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            band_str = (row.get("ml_predicted_band") or "").strip().upper()
            if not band_str:
                continue
            try:
                ml_band = RiskBand(band_str)
            except ValueError:
                raise ValueError(
                    f"row task_id={row.get('task_id')!r} has invalid ml_predicted_band {band_str!r}"
                )
            key = (
                str(row.get("profile_id", "")).strip(),
                str(row.get("scenario_name", "")).strip(),
            )
            ml_bands[key] = ml_band
    return ml_bands


def extract_ml_predicted_bands_json(
    json_path: str | Path,
) -> dict[tuple[str, str], RiskBand]:
    """Read ML reference bands embedded in a review JSON export."""
    path = Path(json_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    ml_bands: dict[tuple[str, str], RiskBand] = {}
    for task in tasks:
        band_str = str(task.get("ml_predicted_band", "")).strip().upper()
        if not band_str:
            continue
        try:
            ml_band = RiskBand(band_str)
        except ValueError:
            raise ValueError(
                f"task_id={task.get('task_id')!r} has invalid ml_predicted_band {band_str!r}"
            )
        key = (
            str(task.get("profile_id", "")).strip(),
            str(task.get("scenario_name", "")).strip(),
        )
        ml_bands[key] = ml_band
    return ml_bands


def extract_ml_predicted_bands(
    path: str | Path,
) -> dict[tuple[str, str], RiskBand]:
    """Read ML reference bands from either a CSV or JSON review export."""
    resolved = Path(path)
    if resolved.suffix.lower() == ".json":
        return extract_ml_predicted_bands_json(resolved)
    return extract_ml_predicted_bands_csv(resolved)


def compute_external_calibration(
    records: list[DatasetRecord],
    ratings: list[ExpertRating],
    ml_predicted_bands: dict[tuple[str, str], RiskBand] | None = None,
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
        raise ValueError(
            "no overlap between ratings and records — check profile_id and scenario_name"
        )

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


def _reviewer_id_from_path(path: str | Path) -> str:
    """Derive a stable reviewer identifier from a completed CSV path."""
    return Path(path).stem


def _mean_or_none(values: list[float | None]) -> float | None:
    """Return the rounded arithmetic mean for non-null values."""
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return round(sum(filtered) / len(filtered), 4)


def _build_consensus_task_summaries(
    ratings_by_reviewer: dict[str, list[ExpertRating]],
) -> list[ConsensusTaskSummary]:
    """Build one consensus summary per reviewed task across all reviewers."""
    grouped: dict[tuple[str, str], list[tuple[str, ExpertRating]]] = defaultdict(list)
    for reviewer_id, ratings in ratings_by_reviewer.items():
        for rating in ratings:
            grouped[(rating.profile_id, rating.scenario_name)].append((reviewer_id, rating))

    summaries: list[ConsensusTaskSummary] = []
    for (_, _), votes in sorted(grouped.items(), key=lambda item: item[0]):
        band_counts = Counter(rating.expert_band for _, rating in votes)
        top_count = max(band_counts.values())
        top_bands = [band for band, count in band_counts.items() if count == top_count]
        consensus_band = max(top_bands, key=lambda band: _BAND_RANK[band])
        representative = votes[0][1]
        summaries.append(
            ConsensusTaskSummary(
                task_id=representative.task_id,
                profile_id=representative.profile_id,
                scenario_name=representative.scenario_name,
                reviewer_count=len(votes),
                consensus_band=consensus_band,
                vote_counts={band.value: count for band, count in band_counts.items()},
                reviewer_bands={
                    reviewer_id: rating.expert_band.value for reviewer_id, rating in votes
                },
                unanimous=len(top_bands) == 1 and top_count == len(votes),
                tie_broken=len(top_bands) > 1,
            )
        )
    return summaries


def _pairwise_band_agreement_rate(
    ratings_by_reviewer: dict[str, list[ExpertRating]],
) -> float | None:
    """Compute mean pairwise reviewer agreement on overlapping tasks."""
    reviewer_ids = sorted(ratings_by_reviewer)
    if len(reviewer_ids) < 2:
        return None

    indexed = {
        reviewer_id: {
            (rating.profile_id, rating.scenario_name): rating.expert_band
            for rating in ratings
        }
        for reviewer_id, ratings in ratings_by_reviewer.items()
    }

    pair_rates: list[float] = []
    for left_id, right_id in combinations(reviewer_ids, 2):
        left = indexed[left_id]
        right = indexed[right_id]
        overlap = sorted(set(left) & set(right))
        if not overlap:
            continue
        matches = sum(1 for key in overlap if left[key] == right[key])
        pair_rates.append(matches / len(overlap))

    if not pair_rates:
        return None
    return round(sum(pair_rates) / len(pair_rates), 4)


def summarize_expert_review_batch(
    records: list[DatasetRecord],
    ratings_files: list[str | Path],
    reference_file: str | Path | None = None,
    require_ml_reference: bool = False,
) -> tuple[
    ExpertReviewBatchSummary,
    list[ReviewerCalibrationSummary],
    list[ConsensusTaskSummary],
]:
    """Summarize multiple completed reviewer CSVs into aggregate calibration metrics."""
    ratings_by_reviewer: dict[str, list[ExpertRating]] = {}
    reviewer_summaries: list[ReviewerCalibrationSummary] = []
    ml_bands_by_task: dict[tuple[str, str], RiskBand] = {}
    shared_reference_bands = (
        extract_ml_predicted_bands(reference_file) if reference_file is not None else None
    )

    for source in ratings_files:
        path = Path(source)
        reviewer_id = _reviewer_id_from_path(path)
        if reviewer_id in ratings_by_reviewer:
            raise ValueError(f"duplicate reviewer identifier derived from path: {reviewer_id}")

        ratings = import_expert_ratings_csv(path)
        if not ratings:
            raise ValueError(f"no completed expert ratings found in {path}")

        reviewer_ml_bands = (
            shared_reference_bands if shared_reference_bands is not None else extract_ml_predicted_bands(path)
        )
        if require_ml_reference and not reviewer_ml_bands:
            raise ValueError(
                f"{path} does not provide recoverable ml_predicted_band values; use a non-blind "
                "review packet or pass the blind packet key via --reference-file"
            )

        for key, band in reviewer_ml_bands.items():
            existing = ml_bands_by_task.get(key)
            if existing is not None and existing != band:
                raise ValueError(
                    f"inconsistent ml_predicted_band values for task {key} across reviewer files"
                )
            ml_bands_by_task[key] = band

        calibration = compute_external_calibration(
            records,
            ratings,
            ml_predicted_bands=reviewer_ml_bands or None,
        )
        reviewer_summaries.append(
            ReviewerCalibrationSummary(
                reviewer_id=reviewer_id,
                source_file=str(path.resolve()),
                rating_count=calibration.rating_count,
                heuristic_vs_expert_match_rate=calibration.heuristic_vs_expert_match_rate,
                ml_vs_expert_match_rate=calibration.ml_vs_expert_match_rate,
                heuristic_vs_ml_match_rate=calibration.heuristic_vs_ml_match_rate,
                severe_disagreement_count=calibration.severe_disagreement_count,
            )
        )
        ratings_by_reviewer[reviewer_id] = ratings

    reviewer_summaries.sort(key=lambda summary: summary.reviewer_id)
    consensus_tasks = _build_consensus_task_summaries(ratings_by_reviewer)
    consensus_ratings = [
        ExpertRating(
            task_id=task.task_id,
            profile_id=task.profile_id,
            scenario_name=task.scenario_name,
            expert_band=task.consensus_band,
        )
        for task in consensus_tasks
    ]
    consensus_result = (
        compute_external_calibration(
            records,
            consensus_ratings,
            ml_predicted_bands=ml_bands_by_task or None,
        )
        if consensus_ratings
        else None
    )

    tasks_per_reviewer = [summary.rating_count for summary in reviewer_summaries]
    multi_reviewer_tasks = [task for task in consensus_tasks if task.reviewer_count > 1]
    overview = ExpertReviewBatchSummary(
        reviewer_count=len(reviewer_summaries),
        unique_task_count=len(consensus_tasks),
        mean_tasks_per_reviewer=round(sum(tasks_per_reviewer) / len(tasks_per_reviewer), 2),
        pairwise_band_agreement_rate=_pairwise_band_agreement_rate(ratings_by_reviewer),
        unanimous_task_rate=(
            round(
                sum(1 for task in multi_reviewer_tasks if task.unanimous)
                / len(multi_reviewer_tasks),
                4,
            )
            if multi_reviewer_tasks
            else None
        ),
        average_heuristic_vs_expert_match_rate=round(
            sum(summary.heuristic_vs_expert_match_rate for summary in reviewer_summaries)
            / len(reviewer_summaries),
            4,
        ),
        average_ml_vs_expert_match_rate=_mean_or_none(
            [summary.ml_vs_expert_match_rate for summary in reviewer_summaries]
        ),
        average_heuristic_vs_ml_match_rate=_mean_or_none(
            [summary.heuristic_vs_ml_match_rate for summary in reviewer_summaries]
        ),
        average_severe_disagreement_count=round(
            sum(summary.severe_disagreement_count for summary in reviewer_summaries)
            / len(reviewer_summaries),
            4,
        ),
        consensus_result=consensus_result,
    )
    return overview, reviewer_summaries, consensus_tasks


def render_expert_review_summary_table(
    overview: ExpertReviewBatchSummary,
    reviewer_summaries: list[ReviewerCalibrationSummary],
) -> str:
    """Render per-reviewer external calibration summaries as markdown."""
    headers = (
        "Reviewer",
        "Ratings",
        "Heuristic vs Expert",
        "ML vs Expert",
        "Heuristic vs ML",
        "Severe Disagreements",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for summary in reviewer_summaries:
        lines.append(
            "| "
            + " | ".join(
                (
                    summary.reviewer_id,
                    str(summary.rating_count),
                    f"{summary.heuristic_vs_expert_match_rate:.2f}",
                    f"{summary.ml_vs_expert_match_rate:.2f}"
                    if summary.ml_vs_expert_match_rate is not None
                    else "n/a",
                    f"{summary.heuristic_vs_ml_match_rate:.2f}"
                    if summary.heuristic_vs_ml_match_rate is not None
                    else "n/a",
                    str(summary.severe_disagreement_count),
                )
            )
            + " |"
        )

    lines.extend(
        (
            "",
            f"- Reviewers: {overview.reviewer_count}",
            f"- Unique tasks: {overview.unique_task_count}",
            f"- Mean tasks per reviewer: {overview.mean_tasks_per_reviewer:.2f}",
            "- Pairwise band agreement: "
            + (
                f"{overview.pairwise_band_agreement_rate:.2f}"
                if overview.pairwise_band_agreement_rate is not None
                else "n/a"
            ),
            "- Unanimous task rate: "
            + (
                f"{overview.unanimous_task_rate:.2f}"
                if overview.unanimous_task_rate is not None
                else "n/a"
            ),
        )
    )
    return "\n".join(lines) + "\n"


def write_expert_review_artifacts(
    overview: ExpertReviewBatchSummary,
    reviewer_summaries: list[ReviewerCalibrationSummary],
    consensus_tasks: list[ConsensusTaskSummary],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> ExpertReviewArtifacts:
    """Persist a timestamped expert-review summary bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_EXPERT_REVIEW_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    summary_path = run_dir / "expert_review_summary.json"
    reviewer_summaries_path = run_dir / "reviewer_summaries.csv"
    consensus_tasks_path = run_dir / "consensus_tasks.csv"
    summary_table_path = run_dir / "summary_table.md"

    summary_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "reviewer_summaries": [summary.to_dict() for summary in reviewer_summaries],
        "consensus_tasks": [task.to_dict() for task in consensus_tasks],
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    reviewer_buffer = StringIO()
    reviewer_writer = csv.DictWriter(
        reviewer_buffer,
        fieldnames=(
            "reviewer_id",
            "source_file",
            "rating_count",
            "heuristic_vs_expert_match_rate",
            "ml_vs_expert_match_rate",
            "heuristic_vs_ml_match_rate",
            "severe_disagreement_count",
        ),
    )
    reviewer_writer.writeheader()
    for summary in reviewer_summaries:
        reviewer_writer.writerow(summary.to_dict())
    reviewer_summaries_path.write_text(reviewer_buffer.getvalue(), encoding="utf-8")

    consensus_buffer = StringIO()
    consensus_writer = csv.DictWriter(
        consensus_buffer,
        fieldnames=(
            "task_id",
            "profile_id",
            "scenario_name",
            "reviewer_count",
            "consensus_band",
            "vote_counts",
            "reviewer_bands",
            "unanimous",
            "tie_broken",
        ),
    )
    consensus_writer.writeheader()
    for task in consensus_tasks:
        row = task.to_dict()
        row["vote_counts"] = json.dumps(row["vote_counts"], sort_keys=True)
        row["reviewer_bands"] = json.dumps(row["reviewer_bands"], sort_keys=True)
        consensus_writer.writerow(row)
    consensus_tasks_path.write_text(consensus_buffer.getvalue(), encoding="utf-8")

    summary_table_path.write_text(
        render_expert_review_summary_table(overview, reviewer_summaries),
        encoding="utf-8",
    )

    return ExpertReviewArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        reviewer_summaries_file=str(reviewer_summaries_path.resolve()),
        consensus_tasks_file=str(consensus_tasks_path.resolve()),
        summary_table_file=str(summary_table_path.resolve()),
    )


def expert_review_batch_to_json(
    overview: ExpertReviewBatchSummary,
    reviewer_summaries: list[ReviewerCalibrationSummary],
    consensus_tasks: list[ConsensusTaskSummary],
    *,
    include_reviewer_summaries: bool = False,
    include_consensus_tasks: bool = False,
    pretty: bool = False,
    summary_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize a batch expert-review summary as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
        "summary_table_markdown": summary_table_markdown,
        "artifacts": artifacts,
    }
    if include_reviewer_summaries:
        payload["reviewer_summaries"] = [summary.to_dict() for summary in reviewer_summaries]
    if include_consensus_tasks:
        payload["consensus_tasks"] = [task.to_dict() for task in consensus_tasks]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
