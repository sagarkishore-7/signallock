"""Higher-level summary helpers for executed SignalLock preset bundles."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .analysis import _create_unique_run_directory
from .paths import artifacts_path
from .reporting import normalize_artifact_path
from .schemas import (
    PolicyProfile,
    PresetCalibrationSummaryRecord,
    PresetComparisonSummaryRecord,
    PresetPolicySummaryRecord,
    PresetResultsArtifacts,
    PresetResultsOverview,
    PresetRunRecord,
)


DEFAULT_PRESET_INPUT_DIR = artifacts_path("presets")
DEFAULT_RESULTS_OUTPUT_DIR = artifacts_path("results")


def summarize_preset_runs(
    input_dir: str | Path | None = None,
    selected_presets: list[str] | None = None,
) -> tuple[
    PresetResultsOverview,
    list[PresetRunRecord],
    list[PresetPolicySummaryRecord],
    list[PresetCalibrationSummaryRecord],
    list[PresetComparisonSummaryRecord],
]:
    """Scan executed preset bundles and flatten them into summary-friendly records."""
    root_dir = normalize_artifact_path(input_dir, DEFAULT_PRESET_INPUT_DIR)
    if not root_dir.exists():
        raise FileNotFoundError(f"preset input directory does not exist: {root_dir}")

    selected = {name.strip() for name in selected_presets or [] if name.strip()}
    run_records: list[PresetRunRecord] = []
    policy_records: list[PresetPolicySummaryRecord] = []
    calibration_records: list[PresetCalibrationSummaryRecord] = []
    comparison_records: list[PresetComparisonSummaryRecord] = []

    for manifest_path in sorted(root_dir.glob("*/preset_manifest.json")):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        preset_name = str(payload.get("preset_name", "")).strip()
        if not preset_name:
            continue
        if selected and preset_name not in selected:
            continue

        baseline_profile = PolicyProfile(str(payload.get("baseline_profile", "balanced")))
        preset_artifacts = payload.get("preset_artifacts", {})
        generated_at = str(payload.get("generated_at", ""))
        run_record = PresetRunRecord(
            preset_run_id=str(preset_artifacts.get("run_id", manifest_path.parent.name)),
            preset_name=preset_name,
            description=str(payload.get("description", "")),
            generated_at=generated_at,
            organization=str(payload.get("organization", "UnknownOrg")),
            profile_count=int(payload.get("profile_count", 0)),
            evaluation_run_count=int(payload.get("evaluation_run_count", 0)),
            seed_count=len(payload.get("seeds", [])),
            baseline_profile=baseline_profile,
            policy_profiles=sorted(str(profile) for profile in payload.get("policy_profiles", [])),
            comparison_candidates=sorted(
                str(profile) for profile in payload.get("comparison_candidates", [])
            ),
            output_dir=str(preset_artifacts.get("output_dir", manifest_path.parent.resolve())),
            manifest_file=str(manifest_path.resolve()),
        )
        run_records.append(run_record)

        calibration_by_policy: dict[str, list[dict[str, object]]] = {}
        for evaluation_artifact in payload.get("evaluation_artifacts", []):
            if not isinstance(evaluation_artifact, dict):
                continue
            calibration_path = evaluation_artifact.get("calibration_summaries_file")
            if not calibration_path:
                continue
            resolved = Path(str(calibration_path))
            if not resolved.exists():
                continue
            for summary in json.loads(resolved.read_text(encoding="utf-8")):
                policy_name = str(summary["policy_profile"])
                calibration_by_policy.setdefault(policy_name, []).append(summary)

        figure_artifacts = payload.get("figure_artifacts", {})
        figure_summary_path = figure_artifacts.get("summary_file")
        if figure_summary_path and Path(figure_summary_path).exists():
            figure_payload = json.loads(Path(figure_summary_path).read_text(encoding="utf-8"))
            for aggregate in figure_payload.get("aggregates", []):
                policy_profile = PolicyProfile(str(aggregate["policy_profile"]))
                policy_records.append(
                    PresetPolicySummaryRecord(
                        preset_run_id=run_record.preset_run_id,
                        preset_name=run_record.preset_name,
                        generated_at=run_record.generated_at,
                        organization=run_record.organization,
                        profile_count=run_record.profile_count,
                        policy_profile=policy_profile,
                        is_baseline_profile=policy_profile == baseline_profile,
                        run_count=int(aggregate["run_count"]),
                        mean_combined_score=float(aggregate["mean_combined_score"]),
                        mean_exposure_score=float(aggregate["mean_exposure_score"]),
                        mean_password_score=float(aggregate["mean_password_score"]),
                        dominant_top_action=str(aggregate["dominant_top_action"]),
                        source_summary_file=str(Path(figure_summary_path).resolve()),
                    )
                )

        for policy_name, calibration_group in sorted(calibration_by_policy.items()):
            calibration_records.append(
                PresetCalibrationSummaryRecord(
                    preset_run_id=run_record.preset_run_id,
                    preset_name=run_record.preset_name,
                    generated_at=run_record.generated_at,
                    organization=run_record.organization,
                    profile_count=run_record.profile_count,
                    policy_profile=PolicyProfile(policy_name),
                    evaluation_run_count=len(calibration_group),
                    mean_within_expected_range_rate=_mean(
                        float(item["within_expected_range_rate"]) for item in calibration_group
                    ),
                    mean_under_hardening_rate=_mean(
                        float(item["under_hardening_rate"]) for item in calibration_group
                    ),
                    mean_over_hardening_rate=_mean(
                        float(item["over_hardening_rate"]) for item in calibration_group
                    ),
                    mean_true_positive_proxy_rate=_mean(
                        float(item["true_positive_proxy_rate"]) for item in calibration_group
                    ),
                    mean_false_positive_proxy_rate=_mean(
                        float(item["false_positive_proxy_rate"]) for item in calibration_group
                    ),
                    mean_step_up_or_higher_rate=_mean(
                        float(item["step_up_or_higher_rate"]) for item in calibration_group
                    ),
                    mean_block_or_higher_rate=_mean(
                        float(item["block_or_higher_rate"]) for item in calibration_group
                    ),
                    mean_action_severity_gap=_mean(
                        float(item["mean_action_severity_gap"]) for item in calibration_group
                    ),
                    source_manifest_file=str(manifest_path.resolve()),
                )
            )

        comparison_artifacts = payload.get("comparison_artifacts")
        if comparison_artifacts:
            comparison_summary_path = comparison_artifacts.get("summary_file")
            if comparison_summary_path and Path(comparison_summary_path).exists():
                comparison_payload = json.loads(
                    Path(comparison_summary_path).read_text(encoding="utf-8")
                )
                for summary in comparison_payload.get("summaries", []):
                    comparison_records.append(
                        PresetComparisonSummaryRecord(
                            preset_run_id=run_record.preset_run_id,
                            preset_name=run_record.preset_name,
                            generated_at=run_record.generated_at,
                            organization=run_record.organization,
                            profile_count=run_record.profile_count,
                            baseline_profile=PolicyProfile(str(summary["baseline_profile"])),
                            candidate_profile=PolicyProfile(str(summary["candidate_profile"])),
                            matched_run_count=int(summary["matched_run_count"]),
                            mean_combined_score_delta=float(
                                summary["mean_combined_score_delta"]
                            ),
                            mean_exposure_score_delta=float(
                                summary["mean_exposure_score_delta"]
                            ),
                            mean_password_score_delta=float(
                                summary["mean_password_score_delta"]
                            ),
                            candidate_higher_combined_ratio=float(
                                summary["candidate_higher_combined_ratio"]
                            ),
                            action_change_count=int(summary["action_change_count"]),
                            dominant_transition=str(summary["dominant_transition"]),
                            source_summary_file=str(Path(comparison_summary_path).resolve()),
                        )
                    )

    run_records.sort(key=lambda record: (record.generated_at, record.preset_run_id))
    policy_records.sort(
        key=lambda record: (record.preset_name, record.generated_at, record.policy_profile.value)
    )
    calibration_records.sort(
        key=lambda record: (record.preset_name, record.generated_at, record.policy_profile.value)
    )
    comparison_records.sort(
        key=lambda record: (
            record.preset_name,
            record.generated_at,
            record.candidate_profile.value,
        )
    )

    overview = PresetResultsOverview(
        input_dir=str(root_dir.resolve()),
        preset_run_count=len(run_records),
        policy_summary_count=len(policy_records),
        calibration_summary_count=len(calibration_records),
        comparison_summary_count=len(comparison_records),
        preset_names=sorted({record.preset_name for record in run_records}),
        organizations=sorted({record.organization for record in run_records}),
        policy_profiles=sorted({record.policy_profile.value for record in policy_records}),
    )
    return overview, run_records, policy_records, calibration_records, comparison_records


def render_preset_run_table(run_records: list[PresetRunRecord]) -> str:
    """Render one row per executed preset bundle as a markdown table."""
    headers = (
        "Preset",
        "Run",
        "Org",
        "Profiles",
        "Seeds",
        "Eval Runs",
        "Policies",
        "Baseline",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in run_records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.preset_name,
                    record.preset_run_id,
                    record.organization,
                    str(record.profile_count),
                    str(record.seed_count),
                    str(record.evaluation_run_count),
                    ", ".join(record.policy_profiles),
                    record.baseline_profile.value,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_preset_policy_table(policy_records: list[PresetPolicySummaryRecord]) -> str:
    """Render per-policy preset summaries as a markdown table."""
    headers = (
        "Preset",
        "Run",
        "Policy",
        "Baseline",
        "Mean Combined",
        "Mean Exposure",
        "Mean Password",
        "Dominant Action",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in policy_records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.preset_name,
                    record.preset_run_id,
                    record.policy_profile.value,
                    "yes" if record.is_baseline_profile else "no",
                    f"{record.mean_combined_score:.2f}",
                    f"{record.mean_exposure_score:.2f}",
                    f"{record.mean_password_score:.2f}",
                    record.dominant_top_action,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_preset_calibration_table(
    calibration_records: list[PresetCalibrationSummaryRecord],
) -> str:
    """Render per-policy preset calibration summaries as a markdown table."""
    headers = (
        "Preset",
        "Run",
        "Policy",
        "Within Range",
        "Under",
        "Over",
        "TP Proxy",
        "FP Proxy",
        "Block+",
        "Mean Gap",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in calibration_records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.preset_name,
                    record.preset_run_id,
                    record.policy_profile.value,
                    f"{record.mean_within_expected_range_rate:.2f}",
                    f"{record.mean_under_hardening_rate:.2f}",
                    f"{record.mean_over_hardening_rate:.2f}",
                    f"{record.mean_true_positive_proxy_rate:.2f}",
                    f"{record.mean_false_positive_proxy_rate:.2f}",
                    f"{record.mean_block_or_higher_rate:.2f}",
                    f"{record.mean_action_severity_gap:+.2f}",
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_preset_comparison_table(
    comparison_records: list[PresetComparisonSummaryRecord],
) -> str:
    """Render per-candidate preset comparisons as a markdown table."""
    headers = (
        "Preset",
        "Run",
        "Baseline",
        "Candidate",
        "Matched Runs",
        "Mean Combined Delta",
        "Action Changes",
        "Dominant Transition",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in comparison_records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.preset_name,
                    record.preset_run_id,
                    record.baseline_profile.value,
                    record.candidate_profile.value,
                    str(record.matched_run_count),
                    f"{record.mean_combined_score_delta:+.2f}",
                    str(record.action_change_count),
                    record.dominant_transition,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_preset_runs_csv(run_records: list[PresetRunRecord]) -> str:
    """Render flattened preset runs as CSV."""
    fieldnames = [
        "preset_run_id",
        "preset_name",
        "description",
        "generated_at",
        "organization",
        "profile_count",
        "evaluation_run_count",
        "seed_count",
        "baseline_profile",
        "policy_profiles",
        "comparison_candidates",
        "output_dir",
        "manifest_file",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for record in run_records:
        row = record.to_dict()
        row["policy_profiles"] = json.dumps(row["policy_profiles"])
        row["comparison_candidates"] = json.dumps(row["comparison_candidates"])
        writer.writerow(row)
    return buffer.getvalue()


def render_preset_policy_csv(policy_records: list[PresetPolicySummaryRecord]) -> str:
    """Render flattened preset policy summaries as CSV."""
    fieldnames = [
        "preset_run_id",
        "preset_name",
        "generated_at",
        "organization",
        "profile_count",
        "policy_profile",
        "is_baseline_profile",
        "run_count",
        "mean_combined_score",
        "mean_exposure_score",
        "mean_password_score",
        "dominant_top_action",
        "source_summary_file",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for record in policy_records:
        writer.writerow(record.to_dict())
    return buffer.getvalue()


def render_preset_comparison_csv(
    comparison_records: list[PresetComparisonSummaryRecord],
) -> str:
    """Render flattened preset comparison summaries as CSV."""
    fieldnames = [
        "preset_run_id",
        "preset_name",
        "generated_at",
        "organization",
        "profile_count",
        "baseline_profile",
        "candidate_profile",
        "matched_run_count",
        "mean_combined_score_delta",
        "mean_exposure_score_delta",
        "mean_password_score_delta",
        "candidate_higher_combined_ratio",
        "action_change_count",
        "dominant_transition",
        "source_summary_file",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for record in comparison_records:
        writer.writerow(record.to_dict())
    return buffer.getvalue()


def render_preset_calibration_csv(
    calibration_records: list[PresetCalibrationSummaryRecord],
) -> str:
    """Render flattened preset calibration summaries as CSV."""
    fieldnames = [
        "preset_run_id",
        "preset_name",
        "generated_at",
        "organization",
        "profile_count",
        "policy_profile",
        "evaluation_run_count",
        "mean_within_expected_range_rate",
        "mean_under_hardening_rate",
        "mean_over_hardening_rate",
        "mean_true_positive_proxy_rate",
        "mean_false_positive_proxy_rate",
        "mean_step_up_or_higher_rate",
        "mean_block_or_higher_rate",
        "mean_action_severity_gap",
        "source_manifest_file",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for record in calibration_records:
        writer.writerow(record.to_dict())
    return buffer.getvalue()


def write_preset_results_artifacts(
    overview: PresetResultsOverview,
    run_records: list[PresetRunRecord],
    policy_records: list[PresetPolicySummaryRecord],
    calibration_records: list[PresetCalibrationSummaryRecord],
    comparison_records: list[PresetComparisonSummaryRecord],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> PresetResultsArtifacts:
    """Persist a timestamped preset-results summary bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_RESULTS_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    preset_table = render_preset_run_table(run_records)
    policy_table = render_preset_policy_table(policy_records)
    calibration_table = render_preset_calibration_table(calibration_records)
    comparison_table = (
        render_preset_comparison_table(comparison_records) if comparison_records else None
    )
    run_csv = render_preset_runs_csv(run_records)
    policy_csv = render_preset_policy_csv(policy_records)
    calibration_csv = render_preset_calibration_csv(calibration_records)
    comparison_csv = render_preset_comparison_csv(comparison_records)

    summary_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "preset_runs": [record.to_dict() for record in run_records],
        "policy_summaries": [record.to_dict() for record in policy_records],
        "calibration_summaries": [record.to_dict() for record in calibration_records],
        "comparison_summaries": [record.to_dict() for record in comparison_records],
        "preset_table_markdown": preset_table,
        "policy_table_markdown": policy_table,
        "calibration_table_markdown": calibration_table,
        "comparison_table_markdown": comparison_table,
    }

    summary_path = run_dir / "preset_results_summary.json"
    preset_runs_path = run_dir / "preset_runs.csv"
    policy_summaries_path = run_dir / "preset_policy_summaries.csv"
    calibration_summaries_path = run_dir / "preset_calibration_summaries.csv"
    comparison_summaries_path = run_dir / "preset_comparison_summaries.csv"
    preset_table_path = run_dir / "preset_summary_table.md"
    policy_table_path = run_dir / "preset_policy_summary_table.md"
    calibration_table_path = run_dir / "preset_calibration_summary_table.md"
    comparison_table_path = (
        run_dir / "preset_comparison_summary_table.md" if comparison_table else None
    )

    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    preset_runs_path.write_text(run_csv, encoding="utf-8")
    policy_summaries_path.write_text(policy_csv, encoding="utf-8")
    calibration_summaries_path.write_text(calibration_csv, encoding="utf-8")
    comparison_summaries_path.write_text(comparison_csv, encoding="utf-8")
    preset_table_path.write_text(preset_table, encoding="utf-8")
    policy_table_path.write_text(policy_table, encoding="utf-8")
    calibration_table_path.write_text(calibration_table, encoding="utf-8")
    if comparison_table_path is not None:
        comparison_table_path.write_text(comparison_table or "", encoding="utf-8")

    return PresetResultsArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        preset_runs_file=str(preset_runs_path.resolve()),
        policy_summaries_file=str(policy_summaries_path.resolve()),
        calibration_summaries_file=str(calibration_summaries_path.resolve()),
        comparison_summaries_file=str(comparison_summaries_path.resolve()),
        preset_table_file=str(preset_table_path.resolve()),
        policy_table_file=str(policy_table_path.resolve()),
        calibration_table_file=str(calibration_table_path.resolve()),
        comparison_table_file=(
            str(comparison_table_path.resolve()) if comparison_table_path is not None else None
        ),
    )


def preset_results_to_json(
    overview: PresetResultsOverview,
    run_records: list[PresetRunRecord],
    policy_records: list[PresetPolicySummaryRecord],
    calibration_records: list[PresetCalibrationSummaryRecord],
    comparison_records: list[PresetComparisonSummaryRecord],
    include_runs: bool = False,
    include_policy_summaries: bool = False,
    include_calibration_summaries: bool = False,
    include_comparison_summaries: bool = False,
    pretty: bool = False,
    preset_table_markdown: str | None = None,
    policy_table_markdown: str | None = None,
    calibration_table_markdown: str | None = None,
    comparison_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize aggregated preset results as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
    }
    if preset_table_markdown is not None:
        payload["preset_table_markdown"] = preset_table_markdown
    if policy_table_markdown is not None:
        payload["policy_table_markdown"] = policy_table_markdown
    if calibration_table_markdown is not None:
        payload["calibration_table_markdown"] = calibration_table_markdown
    if comparison_table_markdown is not None:
        payload["comparison_table_markdown"] = comparison_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_runs:
        payload["preset_runs"] = [record.to_dict() for record in run_records]
    if include_policy_summaries:
        payload["policy_summaries"] = [record.to_dict() for record in policy_records]
    if include_calibration_summaries:
        payload["calibration_summaries"] = [
            record.to_dict() for record in calibration_records
        ]
    if include_comparison_summaries:
        payload["comparison_summaries"] = [record.to_dict() for record in comparison_records]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _mean(values: object) -> float:
    data = [float(value) for value in values]
    if not data:
        return 0.0
    return round(sum(data) / len(data), 2)
