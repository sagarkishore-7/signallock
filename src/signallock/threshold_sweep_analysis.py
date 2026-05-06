"""Cross-run analysis helpers for saved threshold-sweep artifacts."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .analysis import _create_unique_run_directory
from .paths import artifacts_path
from .reporting import normalize_artifact_path
from .schemas import (
    PolicyProfile,
    ThresholdSweepAggregateRecord,
    ThresholdSweepAnalysisArtifacts,
    ThresholdSweepAnalysisOverview,
    ThresholdSweepRunRecord,
)
from .threshold_sweeps import DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR


DEFAULT_THRESHOLD_SWEEP_ANALYSIS_OUTPUT_DIR = artifacts_path("threshold_sweep_analysis")


def analyze_threshold_sweeps(
    input_dir: str | Path | None = None,
    selected_base_profiles: list[PolicyProfile] | None = None,
) -> tuple[
    ThresholdSweepAnalysisOverview,
    list[ThresholdSweepRunRecord],
    list[ThresholdSweepAggregateRecord],
]:
    """Scan saved threshold-sweep bundles and aggregate them across runs."""
    root_dir = normalize_artifact_path(input_dir, DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR)
    if not root_dir.exists():
        raise FileNotFoundError(f"threshold-sweep input directory does not exist: {root_dir}")

    rows: list[ThresholdSweepRunRecord] = []
    run_count = 0

    for summary_path in sorted(root_dir.glob("*/threshold_sweep_summary.json")):
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        overview = payload.get("overview", {})
        records = payload.get("records", [])
        if not records:
            continue

        base_profile = PolicyProfile(str(overview.get("base_profile", "balanced")))
        if selected_base_profiles and base_profile not in selected_base_profiles:
            continue

        run_id = str(payload.get("run_id", summary_path.parent.name))
        generated_at = str(payload.get("generated_at", ""))
        organization = str(overview.get("organization", "UnknownOrg"))
        profile_count = int(overview.get("profile_count", 0))
        seed = overview.get("seed")
        run_count += 1

        for record in records:
            rows.append(
                ThresholdSweepRunRecord(
                    run_id=run_id,
                    generated_at=generated_at,
                    organization=organization,
                    profile_count=profile_count,
                    seed=int(seed) if seed is not None else None,
                    base_profile=base_profile,
                    variant_label=str(record["variant_label"]),
                    threshold_offset=float(record["threshold_offset"]),
                    warn_threshold=float(record["warn_threshold"]),
                    step_up_threshold=float(record["step_up_threshold"]),
                    enforce_mfa_threshold=float(record["enforce_mfa_threshold"]),
                    sample_count=int(record["sample_count"]),
                    scenario_count=int(record["scenario_count"]),
                    average_combined_score=float(record["average_combined_score"]),
                    average_exposure_score=float(record["average_exposure_score"]),
                    average_password_score=float(record["average_password_score"]),
                    top_action=str(record["top_action"]),
                    within_expected_range_rate=float(record["within_expected_range_rate"]),
                    under_hardening_rate=float(record["under_hardening_rate"]),
                    over_hardening_rate=float(record["over_hardening_rate"]),
                    true_positive_proxy_rate=float(record["true_positive_proxy_rate"]),
                    false_positive_proxy_rate=float(record["false_positive_proxy_rate"]),
                    step_up_or_higher_rate=float(record["step_up_or_higher_rate"]),
                    block_or_higher_rate=float(record["block_or_higher_rate"]),
                    mean_action_severity_gap=float(record["mean_action_severity_gap"]),
                    reference_variant_label=str(record.get("reference_variant_label", "")),
                    is_reference_variant=bool(record.get("is_reference_variant", False)),
                    top_action_changed_from_reference=bool(
                        record.get("top_action_changed_from_reference", False)
                    ),
                    within_expected_range_delta=float(
                        record.get("within_expected_range_delta", 0.0)
                    ),
                    under_hardening_delta=float(record.get("under_hardening_delta", 0.0)),
                    over_hardening_delta=float(record.get("over_hardening_delta", 0.0)),
                    true_positive_proxy_delta=float(
                        record.get("true_positive_proxy_delta", 0.0)
                    ),
                    false_positive_proxy_delta=float(
                        record.get("false_positive_proxy_delta", 0.0)
                    ),
                    step_up_or_higher_delta=float(
                        record.get("step_up_or_higher_delta", 0.0)
                    ),
                    block_or_higher_delta=float(record.get("block_or_higher_delta", 0.0)),
                    mean_action_severity_gap_delta=float(
                        record.get("mean_action_severity_gap_delta", 0.0)
                    ),
                    source_summary_file=str(summary_path.resolve()),
                )
            )

    rows.sort(
        key=lambda row: (
            row.generated_at,
            row.run_id,
            row.base_profile.value,
            row.threshold_offset,
        )
    )
    aggregates = _aggregate_threshold_sweep_rows(rows)
    overview = ThresholdSweepAnalysisOverview(
        input_dir=str(root_dir.resolve()),
        run_count=run_count,
        row_count=len(rows),
        aggregate_count=len(aggregates),
        base_profiles=sorted({row.base_profile.value for row in rows}),
        organizations=sorted({row.organization for row in rows}),
    )
    return overview, rows, aggregates


def render_threshold_sweep_run_table(rows: list[ThresholdSweepRunRecord]) -> str:
    """Render flattened threshold-sweep rows as a markdown table."""
    headers = (
        "Run",
        "Base",
        "Offset",
        "Top Action",
        "Within Range",
        "FP Proxy",
        "FP Delta",
        "Block+",
        "Block Delta",
        "Ref",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                (
                    row.run_id,
                    row.base_profile.value,
                    f"{row.threshold_offset:+.2f}",
                    row.top_action,
                    f"{row.within_expected_range_rate:.2f}",
                    f"{row.false_positive_proxy_rate:.2f}",
                    f"{row.false_positive_proxy_delta:+.2f}",
                    f"{row.block_or_higher_rate:.2f}",
                    f"{row.block_or_higher_delta:+.2f}",
                    "yes" if row.is_reference_variant else "no",
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_threshold_sweep_run_csv(rows: list[ThresholdSweepRunRecord]) -> str:
    """Render flattened threshold-sweep rows as CSV."""
    fieldnames = list(rows[0].to_dict().keys()) if rows else []
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    if fieldnames:
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())
    return buffer.getvalue()


def render_threshold_sweep_aggregate_table(
    records: list[ThresholdSweepAggregateRecord],
) -> str:
    """Render aggregated threshold-sweep metrics as a markdown table."""
    headers = (
        "Base",
        "Offset",
        "Runs",
        "Dominant Action",
        "Within Range",
        "Within Delta",
        "FP Proxy",
        "FP Delta",
        "Block+",
        "Block Delta",
        "Action Change",
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
                    record.base_profile.value,
                    f"{record.threshold_offset:+.2f}",
                    str(record.run_count),
                    record.dominant_top_action,
                    f"{record.mean_within_expected_range_rate:.2f}",
                    f"{record.mean_within_expected_range_delta:+.2f}",
                    f"{record.mean_false_positive_proxy_rate:.2f}",
                    f"{record.mean_false_positive_proxy_delta:+.2f}",
                    f"{record.mean_block_or_higher_rate:.2f}",
                    f"{record.mean_block_or_higher_delta:+.2f}",
                    f"{record.top_action_change_rate:.2f}",
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_threshold_sweep_aggregate_csv(
    records: list[ThresholdSweepAggregateRecord],
) -> str:
    """Render aggregated threshold-sweep metrics as CSV."""
    fieldnames = list(records[0].to_dict().keys()) if records else []
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    if fieldnames:
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())
    return buffer.getvalue()


def write_threshold_sweep_analysis_artifacts(
    overview: ThresholdSweepAnalysisOverview,
    rows: list[ThresholdSweepRunRecord],
    aggregates: list[ThresholdSweepAggregateRecord],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> ThresholdSweepAnalysisArtifacts:
    """Persist a timestamped threshold-sweep analysis bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_THRESHOLD_SWEEP_ANALYSIS_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    run_table = render_threshold_sweep_run_table(rows)
    run_csv = render_threshold_sweep_run_csv(rows)
    aggregate_table = render_threshold_sweep_aggregate_table(aggregates)
    aggregate_csv = render_threshold_sweep_aggregate_csv(aggregates)
    payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "rows": [row.to_dict() for row in rows],
        "aggregates": [record.to_dict() for record in aggregates],
        "run_table_markdown": run_table,
        "aggregate_table_markdown": aggregate_table,
    }

    summary_path = run_dir / "threshold_sweep_analysis.json"
    rows_path = run_dir / "threshold_sweep_rows.csv"
    run_table_path = run_dir / "threshold_sweep_run_table.md"
    aggregate_path = run_dir / "threshold_sweep_aggregates.csv"
    aggregate_table_path = run_dir / "threshold_sweep_aggregate_table.md"

    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    rows_path.write_text(run_csv, encoding="utf-8")
    run_table_path.write_text(run_table, encoding="utf-8")
    aggregate_path.write_text(aggregate_csv, encoding="utf-8")
    aggregate_table_path.write_text(aggregate_table, encoding="utf-8")

    return ThresholdSweepAnalysisArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        rows_file=str(rows_path.resolve()),
        run_table_file=str(run_table_path.resolve()),
        aggregate_file=str(aggregate_path.resolve()),
        aggregate_table_file=str(aggregate_table_path.resolve()),
    )


def threshold_sweep_analysis_to_json(
    overview: ThresholdSweepAnalysisOverview,
    rows: list[ThresholdSweepRunRecord],
    aggregates: list[ThresholdSweepAggregateRecord],
    include_rows: bool = False,
    include_aggregates: bool = False,
    pretty: bool = False,
    run_table_markdown: str | None = None,
    aggregate_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize threshold-sweep analysis results as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
    }
    if run_table_markdown is not None:
        payload["run_table_markdown"] = run_table_markdown
    if aggregate_table_markdown is not None:
        payload["aggregate_table_markdown"] = aggregate_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_rows:
        payload["rows"] = [row.to_dict() for row in rows]
    if include_aggregates:
        payload["aggregates"] = [record.to_dict() for record in aggregates]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _aggregate_threshold_sweep_rows(
    rows: list[ThresholdSweepRunRecord],
) -> list[ThresholdSweepAggregateRecord]:
    """Group threshold-sweep rows by base profile and applied offset."""
    grouped: dict[tuple[PolicyProfile, float], list[ThresholdSweepRunRecord]] = {}
    for row in rows:
        grouped.setdefault((row.base_profile, row.threshold_offset), []).append(row)

    aggregates: list[ThresholdSweepAggregateRecord] = []
    for (base_profile, threshold_offset), group in sorted(
        grouped.items(),
        key=lambda item: (item[0][0].value, item[0][1]),
    ):
        top_action_counts = Counter(row.top_action for row in group)
        aggregates.append(
            ThresholdSweepAggregateRecord(
                base_profile=base_profile,
                threshold_offset=threshold_offset,
                run_count=len(group),
                mean_warn_threshold=_mean(row.warn_threshold for row in group),
                mean_step_up_threshold=_mean(row.step_up_threshold for row in group),
                mean_enforce_mfa_threshold=_mean(row.enforce_mfa_threshold for row in group),
                mean_average_combined_score=_mean(
                    row.average_combined_score for row in group
                ),
                mean_within_expected_range_rate=_mean(
                    row.within_expected_range_rate for row in group
                ),
                mean_under_hardening_rate=_mean(row.under_hardening_rate for row in group),
                mean_over_hardening_rate=_mean(row.over_hardening_rate for row in group),
                mean_true_positive_proxy_rate=_mean(
                    row.true_positive_proxy_rate for row in group
                ),
                mean_false_positive_proxy_rate=_mean(
                    row.false_positive_proxy_rate for row in group
                ),
                mean_step_up_or_higher_rate=_mean(
                    row.step_up_or_higher_rate for row in group
                ),
                mean_block_or_higher_rate=_mean(row.block_or_higher_rate for row in group),
                mean_action_severity_gap=_mean(
                    row.mean_action_severity_gap for row in group
                ),
                mean_within_expected_range_delta=_mean(
                    row.within_expected_range_delta for row in group
                ),
                mean_false_positive_proxy_delta=_mean(
                    row.false_positive_proxy_delta for row in group
                ),
                mean_block_or_higher_delta=_mean(
                    row.block_or_higher_delta for row in group
                ),
                dominant_top_action=min(
                    (-count, action) for action, count in top_action_counts.items()
                )[1],
                reference_variant_ratio=_mean(
                    1.0 if row.is_reference_variant else 0.0 for row in group
                ),
                top_action_change_rate=_mean(
                    1.0 if row.top_action_changed_from_reference else 0.0
                    for row in group
                ),
            )
        )
    return aggregates


def _mean(values: object) -> float:
    """Compute a rounded mean from a numeric iterable."""
    data = list(values)
    if not data:
        return 0.0
    return round(sum(float(value) for value in data) / len(data), 2)
