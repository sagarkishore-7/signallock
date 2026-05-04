"""Cross-run analysis helpers for saved SignalLock evaluation artifacts."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .reporting import DEFAULT_EVALUATION_OUTPUT_DIR, normalize_artifact_path
from .schemas import (
    AnalysisArtifacts,
    EvaluationRunAnalysisOverview,
    EvaluationRunSummaryRecord,
    PolicyProfile,
)


DEFAULT_ANALYSIS_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "analysis"


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
    overview = EvaluationRunAnalysisOverview(
        input_dir=str(root_dir.resolve()),
        run_count=run_count,
        row_count=len(rows),
        policy_profiles=sorted({row.policy_profile.value for row in rows}),
        organizations=sorted({row.organization for row in rows}),
    )
    return overview, rows


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


def write_run_analysis_artifacts(
    overview: EvaluationRunAnalysisOverview,
    rows: list[EvaluationRunSummaryRecord],
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

    analysis_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "rows": [row.to_dict() for row in rows],
        "comparison_table_markdown": comparison_table,
    }

    analysis_path = run_dir / "analysis.json"
    comparison_path = run_dir / "comparison_table.md"
    matrix_path = run_dir / "policy_matrix.csv"

    analysis_path.write_text(json.dumps(analysis_payload, indent=2) + "\n", encoding="utf-8")
    comparison_path.write_text(comparison_table, encoding="utf-8")
    matrix_path.write_text(policy_matrix, encoding="utf-8")

    return AnalysisArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        analysis_file=str(analysis_path.resolve()),
        comparison_table_file=str(comparison_path.resolve()),
        policy_matrix_file=str(matrix_path.resolve()),
    )


def analysis_results_to_json(
    overview: EvaluationRunAnalysisOverview,
    rows: list[EvaluationRunSummaryRecord],
    include_rows: bool = False,
    pretty: bool = False,
    comparison_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize a cross-run analysis result as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
    }
    if comparison_table_markdown is not None:
        payload["comparison_table_markdown"] = comparison_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_rows:
        payload["rows"] = [row.to_dict() for row in rows]

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
