"""Paper-oriented aggregate analysis for saved SignalLock preset summaries."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from math import sqrt
from pathlib import Path

from .analysis import _create_unique_run_directory
from .reporting import normalize_artifact_path
from .schemas import (
    CrossPresetComparisonAggregateRecord,
    CrossPresetPolicyAggregateRecord,
    PolicyProfile,
    PresetAggregateArtifacts,
    PresetAggregateOverview,
    PresetComparisonAggregateRecord,
    PresetComparisonSummaryRecord,
    PresetPolicyAggregateRecord,
    PresetPolicySummaryRecord,
    PresetResultsOverview,
    PresetRunRecord,
)


DEFAULT_PRESET_AGGREGATE_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "preset_aggregates"
)


def aggregate_preset_results(
    results_overview: PresetResultsOverview,
    run_records: list[PresetRunRecord],
    policy_records: list[PresetPolicySummaryRecord],
    comparison_records: list[PresetComparisonSummaryRecord],
) -> tuple[
    PresetAggregateOverview,
    list[PresetPolicyAggregateRecord],
    list[PresetComparisonAggregateRecord],
    list[CrossPresetPolicyAggregateRecord],
    list[CrossPresetComparisonAggregateRecord],
]:
    """Aggregate preset-level summaries into paper-friendly grouped records."""
    preset_policy_aggregates = _aggregate_preset_policy_records(policy_records)
    preset_comparison_aggregates = _aggregate_preset_comparison_records(comparison_records)
    cross_policy_aggregates = _aggregate_cross_policy_records(policy_records)
    cross_comparison_aggregates = _aggregate_cross_comparison_records(comparison_records)

    overview = PresetAggregateOverview(
        input_dir=results_overview.input_dir,
        preset_run_count=len(run_records),
        preset_policy_aggregate_count=len(preset_policy_aggregates),
        preset_comparison_aggregate_count=len(preset_comparison_aggregates),
        cross_policy_aggregate_count=len(cross_policy_aggregates),
        cross_comparison_aggregate_count=len(cross_comparison_aggregates),
        preset_names=sorted({record.preset_name for record in run_records}),
        policy_profiles=sorted({record.policy_profile.value for record in policy_records}),
    )
    return (
        overview,
        preset_policy_aggregates,
        preset_comparison_aggregates,
        cross_policy_aggregates,
        cross_comparison_aggregates,
    )


def render_preset_policy_aggregate_table(
    records: list[PresetPolicyAggregateRecord],
) -> str:
    """Render aggregated preset-policy metrics as a markdown table."""
    headers = (
        "Preset",
        "Policy",
        "Runs",
        "Mean Combined",
        "Std Combined",
        "Mean Exposure",
        "Mean Password",
        "Dominant Action",
        "Baseline Ratio",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.preset_name,
                    record.policy_profile.value,
                    str(record.preset_run_count),
                    f"{record.mean_combined_score:.2f}",
                    f"{record.std_combined_score:.2f}",
                    f"{record.mean_exposure_score:.2f}",
                    f"{record.mean_password_score:.2f}",
                    record.dominant_top_action,
                    f"{record.baseline_run_ratio:.2f}",
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_preset_comparison_aggregate_table(
    records: list[PresetComparisonAggregateRecord],
) -> str:
    """Render aggregated preset comparison metrics as a markdown table."""
    headers = (
        "Preset",
        "Baseline",
        "Candidate",
        "Runs",
        "Mean Combined Delta",
        "Std Combined Delta",
        "Higher Ratio",
        "Action Change Ratio",
        "Dominant Transition",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.preset_name,
                    record.baseline_profile.value,
                    record.candidate_profile.value,
                    str(record.preset_run_count),
                    f"{record.mean_combined_score_delta:+.2f}",
                    f"{record.std_combined_score_delta:.2f}",
                    f"{record.mean_candidate_higher_ratio:.2f}",
                    f"{record.mean_action_change_ratio:.2f}",
                    record.dominant_transition,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_cross_policy_aggregate_table(
    records: list[CrossPresetPolicyAggregateRecord],
) -> str:
    """Render cross-preset policy aggregates as a markdown table."""
    headers = (
        "Policy",
        "Preset Families",
        "Preset Runs",
        "Mean Combined",
        "Std Combined",
        "Mean Exposure",
        "Mean Password",
        "Dominant Action",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.policy_profile.value,
                    str(record.preset_name_count),
                    str(record.preset_run_count),
                    f"{record.mean_combined_score:.2f}",
                    f"{record.std_combined_score:.2f}",
                    f"{record.mean_exposure_score:.2f}",
                    f"{record.mean_password_score:.2f}",
                    record.dominant_top_action,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_cross_comparison_aggregate_table(
    records: list[CrossPresetComparisonAggregateRecord],
) -> str:
    """Render cross-preset comparison aggregates as a markdown table."""
    headers = (
        "Baseline",
        "Candidate",
        "Preset Families",
        "Preset Runs",
        "Mean Combined Delta",
        "Std Combined Delta",
        "Higher Ratio",
        "Action Change Ratio",
        "Dominant Transition",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                (
                    record.baseline_profile.value,
                    record.candidate_profile.value,
                    str(record.preset_name_count),
                    str(record.preset_run_count),
                    f"{record.mean_combined_score_delta:+.2f}",
                    f"{record.std_combined_score_delta:.2f}",
                    f"{record.mean_candidate_higher_ratio:.2f}",
                    f"{record.mean_action_change_ratio:.2f}",
                    record.dominant_transition,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_preset_aggregate_artifacts(
    overview: PresetAggregateOverview,
    preset_policy_records: list[PresetPolicyAggregateRecord],
    preset_comparison_records: list[PresetComparisonAggregateRecord],
    cross_policy_records: list[CrossPresetPolicyAggregateRecord],
    cross_comparison_records: list[CrossPresetComparisonAggregateRecord],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> PresetAggregateArtifacts:
    """Persist a timestamped preset aggregate bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_PRESET_AGGREGATE_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    preset_policy_table = render_preset_policy_aggregate_table(preset_policy_records)
    preset_comparison_table = render_preset_comparison_aggregate_table(
        preset_comparison_records
    )
    cross_policy_table = render_cross_policy_aggregate_table(cross_policy_records)
    cross_comparison_table = (
        render_cross_comparison_aggregate_table(cross_comparison_records)
        if cross_comparison_records
        else None
    )

    summary_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "preset_policy_aggregates": [record.to_dict() for record in preset_policy_records],
        "preset_comparison_aggregates": [
            record.to_dict() for record in preset_comparison_records
        ],
        "cross_policy_aggregates": [record.to_dict() for record in cross_policy_records],
        "cross_comparison_aggregates": [
            record.to_dict() for record in cross_comparison_records
        ],
        "preset_policy_table_markdown": preset_policy_table,
        "preset_comparison_table_markdown": preset_comparison_table,
        "cross_policy_table_markdown": cross_policy_table,
        "cross_comparison_table_markdown": cross_comparison_table,
    }

    summary_path = run_dir / "preset_aggregate_summary.json"
    preset_policy_csv_path = run_dir / "preset_policy_aggregates.csv"
    preset_comparison_csv_path = run_dir / "preset_comparison_aggregates.csv"
    cross_policy_csv_path = run_dir / "cross_preset_policy_aggregates.csv"
    cross_comparison_csv_path = run_dir / "cross_preset_comparison_aggregates.csv"
    preset_policy_table_path = run_dir / "preset_policy_aggregate_table.md"
    preset_comparison_table_path = run_dir / "preset_comparison_aggregate_table.md"
    cross_policy_table_path = run_dir / "cross_preset_policy_aggregate_table.md"
    cross_comparison_table_path = (
        run_dir / "cross_preset_comparison_aggregate_table.md"
        if cross_comparison_table
        else None
    )

    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    preset_policy_csv_path.write_text(
        _render_csv(preset_policy_records),
        encoding="utf-8",
    )
    preset_comparison_csv_path.write_text(
        _render_csv(preset_comparison_records),
        encoding="utf-8",
    )
    cross_policy_csv_path.write_text(_render_csv(cross_policy_records), encoding="utf-8")
    cross_comparison_csv_path.write_text(
        _render_csv(cross_comparison_records),
        encoding="utf-8",
    )
    preset_policy_table_path.write_text(preset_policy_table, encoding="utf-8")
    preset_comparison_table_path.write_text(preset_comparison_table, encoding="utf-8")
    cross_policy_table_path.write_text(cross_policy_table, encoding="utf-8")
    if cross_comparison_table_path is not None:
        cross_comparison_table_path.write_text(cross_comparison_table or "", encoding="utf-8")

    return PresetAggregateArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        preset_policy_csv_file=str(preset_policy_csv_path.resolve()),
        preset_comparison_csv_file=str(preset_comparison_csv_path.resolve()),
        cross_policy_csv_file=str(cross_policy_csv_path.resolve()),
        cross_comparison_csv_file=str(cross_comparison_csv_path.resolve()),
        preset_policy_table_file=str(preset_policy_table_path.resolve()),
        preset_comparison_table_file=str(preset_comparison_table_path.resolve()),
        cross_policy_table_file=str(cross_policy_table_path.resolve()),
        cross_comparison_table_file=(
            str(cross_comparison_table_path.resolve())
            if cross_comparison_table_path is not None
            else None
        ),
    )


def preset_aggregate_results_to_json(
    overview: PresetAggregateOverview,
    preset_policy_records: list[PresetPolicyAggregateRecord],
    preset_comparison_records: list[PresetComparisonAggregateRecord],
    cross_policy_records: list[CrossPresetPolicyAggregateRecord],
    cross_comparison_records: list[CrossPresetComparisonAggregateRecord],
    pretty: bool = False,
    include_tables: bool = False,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize preset aggregate analysis results as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
        "preset_policy_aggregates": [record.to_dict() for record in preset_policy_records],
        "preset_comparison_aggregates": [
            record.to_dict() for record in preset_comparison_records
        ],
        "cross_policy_aggregates": [record.to_dict() for record in cross_policy_records],
        "cross_comparison_aggregates": [
            record.to_dict() for record in cross_comparison_records
        ],
    }
    if include_tables:
        payload["preset_policy_table_markdown"] = render_preset_policy_aggregate_table(
            preset_policy_records
        )
        payload["preset_comparison_table_markdown"] = (
            render_preset_comparison_aggregate_table(preset_comparison_records)
        )
        payload["cross_policy_table_markdown"] = render_cross_policy_aggregate_table(
            cross_policy_records
        )
        payload["cross_comparison_table_markdown"] = (
            render_cross_comparison_aggregate_table(cross_comparison_records)
            if cross_comparison_records
            else None
        )
    if artifacts is not None:
        payload["artifacts"] = artifacts

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _aggregate_preset_policy_records(
    records: list[PresetPolicySummaryRecord],
) -> list[PresetPolicyAggregateRecord]:
    grouped: dict[tuple[str, str], list[PresetPolicySummaryRecord]] = {}
    for record in records:
        grouped.setdefault((record.preset_name, record.policy_profile.value), []).append(record)

    aggregates: list[PresetPolicyAggregateRecord] = []
    for (preset_name, _policy_name), group in sorted(grouped.items()):
        action_counts = Counter(record.dominant_top_action for record in group)
        aggregates.append(
            PresetPolicyAggregateRecord(
                preset_name=preset_name,
                policy_profile=group[0].policy_profile,
                preset_run_count=len(group),
                mean_combined_score=_mean(record.mean_combined_score for record in group),
                std_combined_score=_stddev(record.mean_combined_score for record in group),
                mean_exposure_score=_mean(record.mean_exposure_score for record in group),
                mean_password_score=_mean(record.mean_password_score for record in group),
                dominant_top_action=_most_common_value(action_counts),
                baseline_run_ratio=round(
                    sum(1 for record in group if record.is_baseline_profile) / len(group),
                    2,
                ),
            )
        )
    return aggregates


def _aggregate_preset_comparison_records(
    records: list[PresetComparisonSummaryRecord],
) -> list[PresetComparisonAggregateRecord]:
    grouped: dict[tuple[str, str, str], list[PresetComparisonSummaryRecord]] = {}
    for record in records:
        grouped.setdefault(
            (
                record.preset_name,
                record.baseline_profile.value,
                record.candidate_profile.value,
            ),
            [],
        ).append(record)

    aggregates: list[PresetComparisonAggregateRecord] = []
    for key, group in sorted(grouped.items()):
        action_counts = Counter(record.dominant_transition for record in group)
        aggregates.append(
            PresetComparisonAggregateRecord(
                preset_name=key[0],
                baseline_profile=group[0].baseline_profile,
                candidate_profile=group[0].candidate_profile,
                preset_run_count=len(group),
                mean_combined_score_delta=_mean(
                    record.mean_combined_score_delta for record in group
                ),
                std_combined_score_delta=_stddev(
                    record.mean_combined_score_delta for record in group
                ),
                mean_exposure_score_delta=_mean(
                    record.mean_exposure_score_delta for record in group
                ),
                mean_password_score_delta=_mean(
                    record.mean_password_score_delta for record in group
                ),
                mean_candidate_higher_ratio=_mean(
                    record.candidate_higher_combined_ratio for record in group
                ),
                mean_action_change_ratio=_mean(
                    record.action_change_count / max(record.matched_run_count, 1)
                    for record in group
                ),
                dominant_transition=_most_common_value(action_counts),
            )
        )
    return aggregates


def _aggregate_cross_policy_records(
    records: list[PresetPolicySummaryRecord],
) -> list[CrossPresetPolicyAggregateRecord]:
    grouped: dict[str, list[PresetPolicySummaryRecord]] = {}
    for record in records:
        grouped.setdefault(record.policy_profile.value, []).append(record)

    aggregates: list[CrossPresetPolicyAggregateRecord] = []
    for policy_name, group in sorted(grouped.items()):
        action_counts = Counter(record.dominant_top_action for record in group)
        aggregates.append(
            CrossPresetPolicyAggregateRecord(
                policy_profile=group[0].policy_profile,
                preset_name_count=len({record.preset_name for record in group}),
                preset_run_count=len(group),
                mean_combined_score=_mean(record.mean_combined_score for record in group),
                std_combined_score=_stddev(record.mean_combined_score for record in group),
                mean_exposure_score=_mean(record.mean_exposure_score for record in group),
                mean_password_score=_mean(record.mean_password_score for record in group),
                dominant_top_action=_most_common_value(action_counts),
            )
        )
    return aggregates


def _aggregate_cross_comparison_records(
    records: list[PresetComparisonSummaryRecord],
) -> list[CrossPresetComparisonAggregateRecord]:
    grouped: dict[tuple[str, str], list[PresetComparisonSummaryRecord]] = {}
    for record in records:
        grouped.setdefault(
            (record.baseline_profile.value, record.candidate_profile.value),
            [],
        ).append(record)

    aggregates: list[CrossPresetComparisonAggregateRecord] = []
    for _key, group in sorted(grouped.items()):
        transition_counts = Counter(record.dominant_transition for record in group)
        aggregates.append(
            CrossPresetComparisonAggregateRecord(
                baseline_profile=group[0].baseline_profile,
                candidate_profile=group[0].candidate_profile,
                preset_name_count=len({record.preset_name for record in group}),
                preset_run_count=len(group),
                mean_combined_score_delta=_mean(
                    record.mean_combined_score_delta for record in group
                ),
                std_combined_score_delta=_stddev(
                    record.mean_combined_score_delta for record in group
                ),
                mean_exposure_score_delta=_mean(
                    record.mean_exposure_score_delta for record in group
                ),
                mean_password_score_delta=_mean(
                    record.mean_password_score_delta for record in group
                ),
                mean_candidate_higher_ratio=_mean(
                    record.candidate_higher_combined_ratio for record in group
                ),
                mean_action_change_ratio=_mean(
                    record.action_change_count / max(record.matched_run_count, 1)
                    for record in group
                ),
                dominant_transition=_most_common_value(transition_counts),
            )
        )
    return aggregates


def _render_csv(records: list[object]) -> str:
    if not records:
        return ""
    first_row = records[0].to_dict()
    fieldnames = list(first_row.keys())
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow(first_row)
    for record in records[1:]:
        writer.writerow(record.to_dict())
    return buffer.getvalue()


def _mean(values: object) -> float:
    data = list(values)
    if not data:
        return 0.0
    return round(sum(float(value) for value in data) / len(data), 2)


def _stddev(values: object) -> float:
    data = [float(value) for value in values]
    if len(data) <= 1:
        return 0.0
    mean_value = sum(data) / len(data)
    variance = sum((value - mean_value) ** 2 for value in data) / len(data)
    return round(sqrt(variance), 2)


def _most_common_value(counter: Counter[str]) -> str:
    if not counter:
        return "NONE"
    return min((-count, value) for value, count in counter.items())[1]
