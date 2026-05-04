"""Pairwise comparison helpers for policy-profile deltas across saved runs."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .analysis import _create_unique_run_directory
from .reporting import normalize_artifact_path
from .schemas import (
    ComparisonArtifacts,
    EvaluationRunAnalysisOverview,
    EvaluationRunSummaryRecord,
    PolicyComparisonOverview,
    PolicyComparisonRunDelta,
    PolicyComparisonSummary,
    PolicyProfile,
)


DEFAULT_COMPARISON_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "comparisons"

_DELTA_COLORS = {
    "combined": "#28536b",
    "exposure": "#4f772d",
    "password": "#f4a259",
}


def compare_policy_profiles(
    overview: EvaluationRunAnalysisOverview,
    rows: list[EvaluationRunSummaryRecord],
    baseline_profile: PolicyProfile,
    candidate_profiles: list[PolicyProfile] | None = None,
) -> tuple[PolicyComparisonOverview, list[PolicyComparisonSummary], list[PolicyComparisonRunDelta]]:
    """Compare one baseline policy against one or more candidate policies."""
    candidate_profiles = candidate_profiles or [
        PolicyProfile(profile_name)
        for profile_name in overview.policy_profiles
        if profile_name != baseline_profile.value
    ]
    selected_candidates = [profile for profile in candidate_profiles if profile != baseline_profile]

    rows_by_run: dict[str, dict[str, EvaluationRunSummaryRecord]] = {}
    for row in rows:
        rows_by_run.setdefault(row.run_id, {})[row.policy_profile.value] = row

    run_deltas: list[PolicyComparisonRunDelta] = []
    for candidate_profile in selected_candidates:
        for run_id, policy_rows in rows_by_run.items():
            baseline_row = policy_rows.get(baseline_profile.value)
            candidate_row = policy_rows.get(candidate_profile.value)
            if baseline_row is None or candidate_row is None:
                continue

            run_deltas.append(
                PolicyComparisonRunDelta(
                    run_id=run_id,
                    generated_at=baseline_row.generated_at,
                    organization=baseline_row.organization,
                    profile_count=baseline_row.profile_count,
                    seed=baseline_row.seed,
                    baseline_profile=baseline_profile,
                    candidate_profile=candidate_profile,
                    baseline_top_action=baseline_row.top_action,
                    candidate_top_action=candidate_row.top_action,
                    action_changed=baseline_row.top_action != candidate_row.top_action,
                    baseline_combined_score=baseline_row.average_combined_score,
                    candidate_combined_score=candidate_row.average_combined_score,
                    combined_score_delta=round(
                        candidate_row.average_combined_score - baseline_row.average_combined_score,
                        2,
                    ),
                    exposure_score_delta=round(
                        candidate_row.average_exposure_score - baseline_row.average_exposure_score,
                        2,
                    ),
                    password_score_delta=round(
                        candidate_row.average_password_score - baseline_row.average_password_score,
                        2,
                    ),
                )
            )

    run_deltas.sort(
        key=lambda delta: (delta.candidate_profile.value, delta.generated_at, delta.run_id)
    )

    summaries: list[PolicyComparisonSummary] = []
    for candidate_profile in selected_candidates:
        candidate_deltas = [
            delta for delta in run_deltas if delta.candidate_profile == candidate_profile
        ]
        if not candidate_deltas:
            continue

        transition_counts = Counter(
            f"{delta.baseline_top_action}->{delta.candidate_top_action}"
            for delta in candidate_deltas
        )
        matched_run_count = len(candidate_deltas)
        summaries.append(
            PolicyComparisonSummary(
                baseline_profile=baseline_profile,
                candidate_profile=candidate_profile,
                matched_run_count=matched_run_count,
                mean_combined_score_delta=round(
                    sum(delta.combined_score_delta for delta in candidate_deltas)
                    / matched_run_count,
                    2,
                ),
                mean_exposure_score_delta=round(
                    sum(delta.exposure_score_delta for delta in candidate_deltas)
                    / matched_run_count,
                    2,
                ),
                mean_password_score_delta=round(
                    sum(delta.password_score_delta for delta in candidate_deltas)
                    / matched_run_count,
                    2,
                ),
                candidate_higher_combined_ratio=round(
                    sum(1 for delta in candidate_deltas if delta.combined_score_delta > 0)
                    / matched_run_count,
                    2,
                ),
                action_change_count=sum(
                    1 for delta in candidate_deltas if delta.action_changed
                ),
                dominant_transition=_most_common_transition(transition_counts),
                action_transition_counts=dict(sorted(transition_counts.items())),
            )
        )

    comparison_overview = PolicyComparisonOverview(
        input_dir=overview.input_dir,
        baseline_profile=baseline_profile,
        candidate_profiles=[profile.value for profile in selected_candidates],
        total_runs_scanned=overview.run_count,
        matched_run_count=len(run_deltas),
        summary_count=len(summaries),
    )
    return comparison_overview, summaries, run_deltas


def render_policy_comparison_table(
    summaries: list[PolicyComparisonSummary],
) -> str:
    """Render aggregate policy deltas as a markdown table."""
    headers = (
        "Baseline",
        "Candidate",
        "Matched Runs",
        "Mean Combined Delta",
        "Mean Exposure Delta",
        "Mean Password Delta",
        "Candidate Higher Ratio",
        "Action Changes",
        "Dominant Transition",
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
                    summary.baseline_profile.value,
                    summary.candidate_profile.value,
                    str(summary.matched_run_count),
                    f"{summary.mean_combined_score_delta:+.2f}",
                    f"{summary.mean_exposure_score_delta:+.2f}",
                    f"{summary.mean_password_score_delta:+.2f}",
                    f"{summary.candidate_higher_combined_ratio:.2f}",
                    str(summary.action_change_count),
                    summary.dominant_transition,
                )
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def render_policy_comparison_csv(
    run_deltas: list[PolicyComparisonRunDelta],
) -> str:
    """Render per-run comparison deltas as CSV."""
    fieldnames = [
        "run_id",
        "generated_at",
        "organization",
        "profile_count",
        "seed",
        "baseline_profile",
        "candidate_profile",
        "baseline_top_action",
        "candidate_top_action",
        "action_changed",
        "baseline_combined_score",
        "candidate_combined_score",
        "combined_score_delta",
        "exposure_score_delta",
        "password_score_delta",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for delta in run_deltas:
        writer.writerow(delta.to_dict())
    return buffer.getvalue()


def render_policy_comparison_svg(
    baseline_profile: PolicyProfile,
    summaries: list[PolicyComparisonSummary],
) -> str:
    """Render mean candidate-vs-baseline deltas as an SVG chart."""
    if not summaries:
        return _empty_svg(
            f"Policy Delta Summary vs {baseline_profile.value}",
            "No comparison summaries available.",
        )

    width = 960
    height = 560
    left = 100
    top = 80
    plot_width = 760
    plot_height = 340
    bottom = top + plot_height
    values = [
        value
        for summary in summaries
        for value in (
            summary.mean_combined_score_delta,
            summary.mean_exposure_score_delta,
            summary.mean_password_score_delta,
        )
    ]
    max_abs = max(5.0, max(abs(value) for value in values))
    upper_bound = max_abs * 1.15
    zero_y = top + plot_height / 2
    group_width = plot_width / len(summaries)
    cluster_width = min(group_width * 0.68, 132)
    bar_gap = 8
    bar_width = (cluster_width - 2 * bar_gap) / 3

    elements = [
        _svg_header(width, height),
        _chart_title(f"Policy Delta Summary vs {baseline_profile.value}"),
        _axis_frame(left, top, plot_width, plot_height),
        f'<line x1="{left}" y1="{zero_y:.1f}" x2="{left + plot_width}" y2="{zero_y:.1f}" '
        'stroke="#7b8794" stroke-width="1.5" />',
    ]
    elements.extend(_delta_y_axis_labels(left, top, plot_height, upper_bound))

    for index, summary in enumerate(summaries):
        group_left = left + index * group_width + (group_width - cluster_width) / 2
        values_for_summary = [
            ("combined", summary.mean_combined_score_delta),
            ("exposure", summary.mean_exposure_score_delta),
            ("password", summary.mean_password_score_delta),
        ]

        for offset, (label, value) in enumerate(values_for_summary):
            normalized = abs(value) / (2 * upper_bound)
            bar_height = plot_height * normalized
            x = group_left + offset * (bar_width + bar_gap)
            y = zero_y - bar_height if value >= 0 else zero_y
            elements.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                f'height="{bar_height:.1f}" fill="{_DELTA_COLORS[label]}" rx="4" />'
            )
            label_y = y - 8 if value >= 0 else y + bar_height + 16
            elements.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{label_y:.1f}" '
                'font-size="12" text-anchor="middle" fill="#22333b">'
                f"{value:+.1f}</text>"
            )

        center_x = left + index * group_width + group_width / 2
        elements.append(
            f'<text x="{center_x:.1f}" y="{bottom + 28:.1f}" font-size="13" '
            'text-anchor="middle" fill="#22333b">'
            f"{_escape_xml(summary.candidate_profile.value)}</text>"
        )

    legend_items = [
        ("Combined Delta", _DELTA_COLORS["combined"]),
        ("Exposure Delta", _DELTA_COLORS["exposure"]),
        ("Password Delta", _DELTA_COLORS["password"]),
    ]
    elements.extend(_legend(650, 98, legend_items))
    elements.append("</svg>")
    return "\n".join(elements)


def write_policy_comparison_artifacts(
    comparison_overview: PolicyComparisonOverview,
    summaries: list[PolicyComparisonSummary],
    run_deltas: list[PolicyComparisonRunDelta],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> ComparisonArtifacts:
    """Persist a timestamped comparison bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_COMPARISON_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)
    comparison_table = render_policy_comparison_table(summaries)
    run_delta_csv = render_policy_comparison_csv(run_deltas)
    delta_svg = render_policy_comparison_svg(comparison_overview.baseline_profile, summaries)

    summary_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": comparison_overview.to_dict(),
        "summaries": [summary.to_dict() for summary in summaries],
        "comparison_table_markdown": comparison_table,
    }

    summary_path = run_dir / "comparison_summary.json"
    table_path = run_dir / "comparison_table.md"
    run_deltas_path = run_dir / "run_deltas.csv"
    delta_chart_path = run_dir / "comparison_deltas.svg"

    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    table_path.write_text(comparison_table, encoding="utf-8")
    run_deltas_path.write_text(run_delta_csv, encoding="utf-8")
    delta_chart_path.write_text(delta_svg, encoding="utf-8")

    return ComparisonArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        comparison_table_file=str(table_path.resolve()),
        run_deltas_file=str(run_deltas_path.resolve()),
        delta_chart_file=str(delta_chart_path.resolve()),
    )


def comparison_results_to_json(
    comparison_overview: PolicyComparisonOverview,
    summaries: list[PolicyComparisonSummary],
    run_deltas: list[PolicyComparisonRunDelta],
    include_run_deltas: bool = False,
    pretty: bool = False,
    comparison_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize policy-comparison results as JSON."""
    payload: dict[str, object] = {
        "overview": comparison_overview.to_dict(),
        "summaries": [summary.to_dict() for summary in summaries],
    }
    if comparison_table_markdown is not None:
        payload["comparison_table_markdown"] = comparison_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_run_deltas:
        payload["run_deltas"] = [delta.to_dict() for delta in run_deltas]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _most_common_transition(transition_counts: Counter[str]) -> str:
    """Return a stable most-common transition label."""
    if not transition_counts:
        return "NONE"
    return min((-count, transition) for transition, count in transition_counts.items())[1]


def _svg_header(width: int, height: int) -> str:
    """Return a shared SVG header."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        '<rect width="100%" height="100%" fill="#f8fbff" />'
    )


def _chart_title(title: str) -> str:
    """Return a shared chart title element."""
    return (
        '<text x="60" y="38" font-size="24" font-weight="700" fill="#102a43">'
        f"{_escape_xml(title)}</text>"
    )


def _axis_frame(left: int, top: int, plot_width: int, plot_height: int) -> str:
    """Render axis lines and light grid background."""
    lines = [
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" '
        'fill="#ffffff" stroke="#d9e2ec" stroke-width="1.2" />'
    ]
    for step in range(1, 4):
        y = top + plot_height * step / 4
        lines.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" '
            'stroke="#e9eef5" stroke-width="1" />'
        )
    return "\n".join(lines)


def _delta_y_axis_labels(left: int, top: int, plot_height: int, upper_bound: float) -> list[str]:
    """Render symmetric delta axis labels around zero."""
    labels: list[str] = []
    label_points = (
        (0.0, upper_bound),
        (0.25, upper_bound / 2),
        (0.5, 0.0),
        (0.75, -upper_bound / 2),
        (1.0, -upper_bound),
    )
    for fraction, value in label_points:
        y = top + plot_height * fraction
        labels.append(
            f'<text x="{left - 14}" y="{y + 4:.1f}" font-size="12" text-anchor="end" '
            'fill="#486581">'
            f"{value:+.1f}</text>"
        )
    return labels


def _legend(x: int, y: int, items: list[tuple[str, str]]) -> list[str]:
    """Render a compact legend."""
    elements: list[str] = []
    for index, (label, color) in enumerate(items):
        offset_y = y + index * 22
        elements.append(
            f'<rect x="{x}" y="{offset_y - 10}" width="12" height="12" fill="{color}" rx="2" />'
        )
        elements.append(
            f'<text x="{x + 20}" y="{offset_y}" font-size="12" fill="#22333b">'
            f"{_escape_xml(label)}</text>"
        )
    return elements


def _empty_svg(title: str, message: str) -> str:
    """Render a placeholder SVG when no data is available."""
    return "\n".join(
        [
            _svg_header(960, 220),
            _chart_title(title),
            '<text x="60" y="120" font-size="16" fill="#486581">'
            f"{_escape_xml(message)}</text>",
            "</svg>",
        ]
    )


def _escape_xml(value: str) -> str:
    """Escape XML special characters for SVG text nodes."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
