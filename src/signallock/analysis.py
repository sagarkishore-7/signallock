"""Cross-run analysis helpers for saved SignalLock evaluation artifacts."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .paths import artifacts_path
from .reporting import DEFAULT_EVALUATION_OUTPUT_DIR, normalize_artifact_path
from .schemas import (
    AnalysisArtifacts,
    EvaluationRunCalibrationRecord,
    EvaluationRunAnalysisOverview,
    EvaluationRunSummaryRecord,
    PolicyProfile,
)


DEFAULT_ANALYSIS_OUTPUT_DIR = artifacts_path("analysis")


def analyze_evaluation_runs(
    input_dir: str | Path | None = None,
    selected_profiles: list[PolicyProfile] | None = None,
) -> tuple[EvaluationRunAnalysisOverview, list[EvaluationRunSummaryRecord]]:
    """Scan saved evaluation runs and flatten them into comparison-friendly rows."""
    root_dir = normalize_artifact_path(input_dir, DEFAULT_EVALUATION_OUTPUT_DIR)
    if not root_dir.exists():
        raise FileNotFoundError(f"evaluation input directory does not exist: {root_dir}")

    rows: list[EvaluationRunSummaryRecord] = []
    run_count = 0

    for report_path in sorted(root_dir.glob("*/report.json")):
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        summaries = payload.get("summaries", [])
        if not summaries:
            continue

        metadata = payload.get("metadata", {})
        run_id = str(payload.get("run_id", report_path.parent.name))
        generated_at = str(payload.get("generated_at", ""))
        organization = str(metadata.get("organization", "UnknownOrg"))
        profile_count = int(metadata.get("profile_count", 0))
        seed = metadata.get("seed")
        run_count += 1

        for summary in summaries:
            policy_profile = PolicyProfile(summary["policy_profile"])
            if selected_profiles and policy_profile not in selected_profiles:
                continue

            rows.append(
                EvaluationRunSummaryRecord(
                    run_id=run_id,
                    generated_at=generated_at,
                    organization=organization,
                    profile_count=profile_count,
                    seed=int(seed) if seed is not None else None,
                    policy_profile=policy_profile,
                    sample_count=int(summary["sample_count"]),
                    scenario_count=int(summary["scenario_count"]),
                    average_combined_score=float(summary["average_combined_score"]),
                    average_exposure_score=float(summary["average_exposure_score"]),
                    average_password_score=float(summary["average_password_score"]),
                    top_action=_top_action(summary.get("primary_action_counts", {})),
                    source_report_file=str(report_path.resolve()),
                )
            )

    rows.sort(key=lambda row: (row.generated_at, row.run_id, row.policy_profile.value))
    calibration_rows = analyze_evaluation_calibration_runs(
        input_dir=root_dir,
        selected_profiles=selected_profiles,
    )
    overview = EvaluationRunAnalysisOverview(
        input_dir=str(root_dir.resolve()),
        run_count=run_count,
        row_count=len(rows),
        calibration_row_count=len(calibration_rows),
        policy_profiles=sorted({row.policy_profile.value for row in rows}),
        organizations=sorted({row.organization for row in rows}),
    )
    return overview, rows


def analyze_evaluation_calibration_runs(
    input_dir: str | Path | None = None,
    selected_profiles: list[PolicyProfile] | None = None,
) -> list[EvaluationRunCalibrationRecord]:
    """Scan saved evaluation runs and flatten calibration summaries into analysis rows."""
    root_dir = normalize_artifact_path(input_dir, DEFAULT_EVALUATION_OUTPUT_DIR)
    if not root_dir.exists():
        raise FileNotFoundError(f"evaluation input directory does not exist: {root_dir}")

    rows: list[EvaluationRunCalibrationRecord] = []
    for report_path in sorted(root_dir.glob("*/report.json")):
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        calibration_summaries = payload.get("calibration_summaries", [])
        if not calibration_summaries:
            continue

        metadata = payload.get("metadata", {})
        run_id = str(payload.get("run_id", report_path.parent.name))
        generated_at = str(payload.get("generated_at", ""))
        organization = str(metadata.get("organization", "UnknownOrg"))
        profile_count = int(metadata.get("profile_count", 0))
        seed = metadata.get("seed")

        for summary in calibration_summaries:
            policy_profile = PolicyProfile(summary["policy_profile"])
            if selected_profiles and policy_profile not in selected_profiles:
                continue
            rows.append(
                EvaluationRunCalibrationRecord(
                    run_id=run_id,
                    generated_at=generated_at,
                    organization=organization,
                    profile_count=profile_count,
                    seed=int(seed) if seed is not None else None,
                    policy_profile=policy_profile,
                    total_records=int(summary["total_records"]),
                    high_risk_record_count=int(summary["high_risk_record_count"]),
                    low_risk_record_count=int(summary["low_risk_record_count"]),
                    within_expected_range_rate=float(summary["within_expected_range_rate"]),
                    under_hardening_rate=float(summary["under_hardening_rate"]),
                    over_hardening_rate=float(summary["over_hardening_rate"]),
                    true_positive_proxy_rate=float(summary["true_positive_proxy_rate"]),
                    false_positive_proxy_rate=float(summary["false_positive_proxy_rate"]),
                    warn_or_higher_rate=float(summary["warn_or_higher_rate"]),
                    step_up_or_higher_rate=float(summary["step_up_or_higher_rate"]),
                    block_or_higher_rate=float(summary["block_or_higher_rate"]),
                    mean_action_severity_gap=float(summary["mean_action_severity_gap"]),
                    source_report_file=str(report_path.resolve()),
                )
            )

    rows.sort(key=lambda row: (row.generated_at, row.run_id, row.policy_profile.value))
    return rows


def render_run_analysis_table(rows: list[EvaluationRunSummaryRecord]) -> str:
    """Render flattened run rows as a markdown comparison table."""
    headers = (
        "Run",
        "Policy",
        "Org",
        "Profiles",
        "Avg Combined",
        "Avg Exposure",
        "Avg Password",
        "Top Action",
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
                    row.policy_profile.value,
                    row.organization,
                    str(row.profile_count),
                    f"{row.average_combined_score:.2f}",
                    f"{row.average_exposure_score:.2f}",
                    f"{row.average_password_score:.2f}",
                    row.top_action,
                )
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def render_run_analysis_csv(rows: list[EvaluationRunSummaryRecord]) -> str:
    """Render flattened run rows as CSV for later plotting or statistics work."""
    fieldnames = [
        "run_id",
        "generated_at",
        "organization",
        "profile_count",
        "seed",
        "policy_profile",
        "sample_count",
        "scenario_count",
        "average_combined_score",
        "average_exposure_score",
        "average_password_score",
        "top_action",
        "source_report_file",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row.to_dict())
    return buffer.getvalue()


def render_run_calibration_table(rows: list[EvaluationRunCalibrationRecord]) -> str:
    """Render flattened calibration rows as a markdown comparison table."""
    headers = (
        "Run",
        "Policy",
        "Within Range",
        "Under",
        "Over",
        "TP Proxy",
        "FP Proxy",
        "Step-Up+",
        "Block+",
        "Mean Gap",
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
                    row.policy_profile.value,
                    f"{row.within_expected_range_rate:.2f}",
                    f"{row.under_hardening_rate:.2f}",
                    f"{row.over_hardening_rate:.2f}",
                    f"{row.true_positive_proxy_rate:.2f}",
                    f"{row.false_positive_proxy_rate:.2f}",
                    f"{row.step_up_or_higher_rate:.2f}",
                    f"{row.block_or_higher_rate:.2f}",
                    f"{row.mean_action_severity_gap:+.2f}",
                )
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def render_run_calibration_csv(rows: list[EvaluationRunCalibrationRecord]) -> str:
    """Render flattened calibration rows as CSV."""
    fieldnames = [
        "run_id",
        "generated_at",
        "organization",
        "profile_count",
        "seed",
        "policy_profile",
        "total_records",
        "high_risk_record_count",
        "low_risk_record_count",
        "within_expected_range_rate",
        "under_hardening_rate",
        "over_hardening_rate",
        "true_positive_proxy_rate",
        "false_positive_proxy_rate",
        "warn_or_higher_rate",
        "step_up_or_higher_rate",
        "block_or_higher_rate",
        "mean_action_severity_gap",
        "source_report_file",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row.to_dict())
    return buffer.getvalue()


def write_run_analysis_artifacts(
    overview: EvaluationRunAnalysisOverview,
    rows: list[EvaluationRunSummaryRecord],
    calibration_rows: list[EvaluationRunCalibrationRecord] | None = None,
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> AnalysisArtifacts:
    """Persist a timestamped cross-run analysis bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_ANALYSIS_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)
    comparison_table = render_run_analysis_table(rows)
    policy_matrix = render_run_analysis_csv(rows)
    calibration_rows = calibration_rows or []
    calibration_table = render_run_calibration_table(calibration_rows)
    calibration_matrix = render_run_calibration_csv(calibration_rows)

    analysis_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "rows": [row.to_dict() for row in rows],
        "comparison_table_markdown": comparison_table,
        "calibration_rows": [row.to_dict() for row in calibration_rows],
        "calibration_table_markdown": calibration_table,
    }

    analysis_path = run_dir / "analysis.json"
    comparison_path = run_dir / "comparison_table.md"
    matrix_path = run_dir / "policy_matrix.csv"
    calibration_table_path = run_dir / "calibration_table.md"
    calibration_matrix_path = run_dir / "calibration_matrix.csv"

    analysis_path.write_text(json.dumps(analysis_payload, indent=2) + "\n", encoding="utf-8")
    comparison_path.write_text(comparison_table, encoding="utf-8")
    matrix_path.write_text(policy_matrix, encoding="utf-8")
    calibration_table_path.write_text(calibration_table, encoding="utf-8")
    calibration_matrix_path.write_text(calibration_matrix, encoding="utf-8")

    return AnalysisArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        analysis_file=str(analysis_path.resolve()),
        comparison_table_file=str(comparison_path.resolve()),
        policy_matrix_file=str(matrix_path.resolve()),
        calibration_table_file=str(calibration_table_path.resolve()),
        calibration_matrix_file=str(calibration_matrix_path.resolve()),
    )


def analysis_results_to_json(
    overview: EvaluationRunAnalysisOverview,
    rows: list[EvaluationRunSummaryRecord],
    calibration_rows: list[EvaluationRunCalibrationRecord] | None = None,
    include_rows: bool = False,
    pretty: bool = False,
    comparison_table_markdown: str | None = None,
    calibration_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize a cross-run analysis result as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
    }
    if comparison_table_markdown is not None:
        payload["comparison_table_markdown"] = comparison_table_markdown
    if calibration_table_markdown is not None:
        payload["calibration_table_markdown"] = calibration_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_rows:
        payload["rows"] = [row.to_dict() for row in rows]
        payload["calibration_rows"] = [
            row.to_dict() for row in (calibration_rows or [])
        ]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _create_unique_run_directory(root_dir: Path, base_run_id: str) -> tuple[Path, str]:
    """Create a timestamped analysis directory, avoiding collisions within the same second."""
    root_dir.mkdir(parents=True, exist_ok=True)

    for index in range(0, 1000):
        run_id = base_run_id if index == 0 else f"{base_run_id}-{index:02d}"
        run_dir = root_dir / run_id
        if not run_dir.exists():
            run_dir.mkdir()
            return run_dir, run_id

    raise RuntimeError("unable to allocate a unique analysis directory")


def _top_action(primary_action_counts: dict[str, int]) -> str:
    """Return the most frequent action from a serialized summary payload."""
    if not primary_action_counts:
        return "NONE"

    return min(
        (-count, action)
        for action, count in primary_action_counts.items()
    )[1]
