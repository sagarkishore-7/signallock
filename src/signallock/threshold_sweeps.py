"""Threshold-sweep experiments for calibration sensitivity analysis."""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .analysis import _create_unique_run_directory
from .evaluation import evaluate_policy_config
from .paths import artifacts_path
from .policy import get_policy_config
from .reporting import normalize_artifact_path
from .schemas import (
    PolicyConfig,
    PolicyProfile,
    PublicProfile,
    ThresholdSweepArtifacts,
    ThresholdSweepOverview,
    ThresholdSweepRecord,
)


DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR = artifacts_path("threshold_sweeps")


def run_threshold_sweep(
    profiles: list[PublicProfile],
    base_profile: PolicyProfile,
    threshold_offsets: list[float],
    organization: str,
    seed: int | None = None,
    policy_file: str | Path | None = None,
) -> tuple[ThresholdSweepOverview, list[ThresholdSweepRecord]]:
    """Evaluate one base policy profile over multiple threshold offsets."""
    base_config = get_policy_config(base_profile, policy_file=policy_file)
    records: list[ThresholdSweepRecord] = []
    resolved_offsets: list[float] = []

    for requested_offset in threshold_offsets:
        variant_config, applied_offset = _variant_for_offset(base_config, requested_offset)
        summary, _, calibration = evaluate_policy_config(profiles, variant_config)
        resolved_offsets.append(applied_offset)
        records.append(
            ThresholdSweepRecord(
                variant_label=_variant_label(base_profile, applied_offset),
                base_profile=base_profile,
                threshold_offset=applied_offset,
                warn_threshold=variant_config.warn_threshold,
                step_up_threshold=variant_config.step_up_threshold,
                enforce_mfa_threshold=variant_config.enforce_mfa_threshold,
                sample_count=summary.sample_count,
                scenario_count=summary.scenario_count,
                average_combined_score=summary.average_combined_score,
                average_exposure_score=summary.average_exposure_score,
                average_password_score=summary.average_password_score,
                top_action=_top_action(summary.primary_action_counts),
                within_expected_range_rate=calibration.within_expected_range_rate,
                under_hardening_rate=calibration.under_hardening_rate,
                over_hardening_rate=calibration.over_hardening_rate,
                true_positive_proxy_rate=calibration.true_positive_proxy_rate,
                false_positive_proxy_rate=calibration.false_positive_proxy_rate,
                step_up_or_higher_rate=calibration.step_up_or_higher_rate,
                block_or_higher_rate=calibration.block_or_higher_rate,
                mean_action_severity_gap=calibration.mean_action_severity_gap,
            )
        )

    overview = ThresholdSweepOverview(
        base_profile=base_profile,
        organization=organization,
        profile_count=len(profiles),
        seed=seed,
        threshold_offsets=resolved_offsets,
        variant_count=len(records),
        policy_file=str(Path(policy_file).resolve()) if policy_file else None,
    )
    records.sort(key=lambda record: record.threshold_offset)
    _attach_reference_deltas(records)
    return overview, records


def render_threshold_sweep_table(records: list[ThresholdSweepRecord]) -> str:
    """Render threshold-sweep results as a markdown table."""
    headers = (
        "Variant",
        "Ref",
        "Offset",
        "Warn",
        "Step-Up",
        "Enforce MFA",
        "Top Action",
        "Within Range",
        "Within Delta",
        "Under",
        "Over",
        "TP Proxy",
        "FP Proxy",
        "FP Delta",
        "Block+",
        "Block Delta",
        "Mean Gap",
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
                    record.variant_label,
                    "yes" if record.is_reference_variant else "no",
                    f"{record.threshold_offset:+.2f}",
                    f"{record.warn_threshold:.2f}",
                    f"{record.step_up_threshold:.2f}",
                    f"{record.enforce_mfa_threshold:.2f}",
                    record.top_action,
                    f"{record.within_expected_range_rate:.2f}",
                    f"{record.within_expected_range_delta:+.2f}",
                    f"{record.under_hardening_rate:.2f}",
                    f"{record.over_hardening_rate:.2f}",
                    f"{record.true_positive_proxy_rate:.2f}",
                    f"{record.false_positive_proxy_rate:.2f}",
                    f"{record.false_positive_proxy_delta:+.2f}",
                    f"{record.block_or_higher_rate:.2f}",
                    f"{record.block_or_higher_delta:+.2f}",
                    f"{record.mean_action_severity_gap:+.2f}",
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_threshold_sweep_csv(records: list[ThresholdSweepRecord]) -> str:
    """Render threshold-sweep results as CSV."""
    fieldnames = list(records[0].to_dict().keys()) if records else []
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    if fieldnames:
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())
    return buffer.getvalue()


def write_threshold_sweep_artifacts(
    overview: ThresholdSweepOverview,
    records: list[ThresholdSweepRecord],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> ThresholdSweepArtifacts:
    """Persist a timestamped threshold-sweep bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)
    table = render_threshold_sweep_table(records)
    csv_text = render_threshold_sweep_csv(records)

    payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "records": [record.to_dict() for record in records],
        "table_markdown": table,
    }

    summary_path = run_dir / "threshold_sweep_summary.json"
    records_path = run_dir / "threshold_sweep_records.csv"
    table_path = run_dir / "threshold_sweep_table.md"

    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    records_path.write_text(csv_text, encoding="utf-8")
    table_path.write_text(table, encoding="utf-8")

    return ThresholdSweepArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        records_file=str(records_path.resolve()),
        table_file=str(table_path.resolve()),
    )


def threshold_sweep_results_to_json(
    overview: ThresholdSweepOverview,
    records: list[ThresholdSweepRecord],
    include_table: bool = False,
    pretty: bool = False,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize threshold-sweep results as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
        "records": [record.to_dict() for record in records],
    }
    if include_table:
        payload["table_markdown"] = render_threshold_sweep_table(records)
    if artifacts is not None:
        payload["artifacts"] = artifacts

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _variant_for_offset(base_config: PolicyConfig, requested_offset: float) -> tuple[PolicyConfig, float]:
    """Build one threshold-shifted policy variant while preserving valid bounds."""
    min_offset = -base_config.warn_threshold
    max_offset = 100.0 - base_config.enforce_mfa_threshold
    applied_offset = round(max(min(requested_offset, max_offset), min_offset), 2)

    return (
        replace(
            base_config,
            warn_threshold=round(base_config.warn_threshold + applied_offset, 2),
            step_up_threshold=round(base_config.step_up_threshold + applied_offset, 2),
            enforce_mfa_threshold=round(base_config.enforce_mfa_threshold + applied_offset, 2),
        ),
        applied_offset,
    )


def _variant_label(base_profile: PolicyProfile, offset: float) -> str:
    """Build a stable label for one threshold-sweep variant."""
    sign = "plus" if offset >= 0 else "minus"
    magnitude = str(abs(offset)).replace(".", "_")
    return f"{base_profile.value}_{sign}_{magnitude}"


def _top_action(primary_action_counts: dict[str, int]) -> str:
    """Return the most frequent primary action for one summary."""
    if not primary_action_counts:
        return "NONE"
    return min((-count, action) for action, count in primary_action_counts.items())[1]


def _attach_reference_deltas(records: list[ThresholdSweepRecord]) -> None:
    """Annotate sweep records with deltas against the nearest-to-zero offset variant."""
    if not records:
        return

    reference_record = min(
        records,
        key=lambda record: (
            abs(record.threshold_offset),
            0 if record.threshold_offset == 0.0 else 1,
            record.threshold_offset,
        ),
    )

    for record in records:
        record.reference_variant_label = reference_record.variant_label
        record.is_reference_variant = record.variant_label == reference_record.variant_label
        record.top_action_changed_from_reference = record.top_action != reference_record.top_action
        record.within_expected_range_delta = round(
            record.within_expected_range_rate - reference_record.within_expected_range_rate,
            2,
        )
        record.under_hardening_delta = round(
            record.under_hardening_rate - reference_record.under_hardening_rate,
            2,
        )
        record.over_hardening_delta = round(
            record.over_hardening_rate - reference_record.over_hardening_rate,
            2,
        )
        record.true_positive_proxy_delta = round(
            record.true_positive_proxy_rate - reference_record.true_positive_proxy_rate,
            2,
        )
        record.false_positive_proxy_delta = round(
            record.false_positive_proxy_rate - reference_record.false_positive_proxy_rate,
            2,
        )
        record.step_up_or_higher_delta = round(
            record.step_up_or_higher_rate - reference_record.step_up_or_higher_rate,
            2,
        )
        record.block_or_higher_delta = round(
            record.block_or_higher_rate - reference_record.block_or_higher_rate,
            2,
        )
        record.mean_action_severity_gap_delta = round(
            record.mean_action_severity_gap - reference_record.mean_action_severity_gap,
            2,
        )
