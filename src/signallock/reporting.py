"""Reporting helpers for reproducible SignalLock evaluation runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .schemas import EvaluationArtifacts, PolicyEvaluationRecord, PolicyEvaluationSummary


DEFAULT_EVALUATION_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "evaluations"
)


def render_policy_comparison_table(
    summaries: list[PolicyEvaluationSummary],
) -> str:
    """Render evaluation summaries as a compact markdown table."""
    headers = (
        "Policy",
        "Samples",
        "Scenarios",
        "Avg Combined",
        "Avg Exposure",
        "Avg Password",
        "Top Action",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for summary in summaries:
        lines.append(
            "| "
            + " | ".join(
                (
                    summary.policy_profile.value,
                    str(summary.sample_count),
                    str(summary.scenario_count),
                    f"{summary.average_combined_score:.2f}",
                    f"{summary.average_exposure_score:.2f}",
                    f"{summary.average_password_score:.2f}",
                    _top_action(summary),
                )
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def write_evaluation_artifacts(
    summaries: list[PolicyEvaluationSummary],
    records: list[PolicyEvaluationRecord],
    output_dir: str | Path | None = None,
    include_records: bool = False,
    metadata: dict[str, object] | None = None,
    generated_at: datetime | None = None,
) -> EvaluationArtifacts:
    """Persist a timestamped evaluation run to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = Path(output_dir) if output_dir else DEFAULT_EVALUATION_OUTPUT_DIR
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)
    comparison_table = render_policy_comparison_table(summaries)

    report_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "metadata": metadata or {},
        "comparison_table_markdown": comparison_table,
        "summaries": [summary.to_dict() for summary in summaries],
    }
    if include_records:
        report_payload["records"] = [record.to_dict() for record in records]

    report_path = run_dir / "report.json"
    summaries_path = run_dir / "summaries.json"
    comparison_path = run_dir / "comparison_table.md"
    records_path = run_dir / "records.json"

    report_path.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")
    summaries_path.write_text(
        json.dumps([summary.to_dict() for summary in summaries], indent=2) + "\n",
        encoding="utf-8",
    )
    comparison_path.write_text(comparison_table, encoding="utf-8")

    artifact_records_path: str | None = None
    if include_records:
        records_path.write_text(
            json.dumps([record.to_dict() for record in records], indent=2) + "\n",
            encoding="utf-8",
        )
        artifact_records_path = str(records_path.resolve())

    return EvaluationArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        report_file=str(report_path.resolve()),
        summaries_file=str(summaries_path.resolve()),
        comparison_table_file=str(comparison_path.resolve()),
        records_file=artifact_records_path,
    )


def _create_unique_run_directory(root_dir: Path, base_run_id: str) -> tuple[Path, str]:
    """Create a timestamped run directory, avoiding collisions within the same second."""
    root_dir.mkdir(parents=True, exist_ok=True)

    for index in range(0, 1000):
        run_id = base_run_id if index == 0 else f"{base_run_id}-{index:02d}"
        run_dir = root_dir / run_id
        if not run_dir.exists():
            run_dir.mkdir()
            return run_dir, run_id

    raise RuntimeError("unable to allocate a unique evaluation run directory")


def _top_action(summary: PolicyEvaluationSummary) -> str:
    """Return the most frequent primary action for a summary."""
    if not summary.primary_action_counts:
        return "NONE"

    return min(
        (
            (-count, action)
            for action, count in summary.primary_action_counts.items()
        )
    )[1]
