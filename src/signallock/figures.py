"""Lightweight figure generation for SignalLock experiment outputs."""

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
    EvaluationRunAnalysisOverview,
    EvaluationRunSummaryRecord,
    FigureArtifacts,
    PolicyAggregateRecord,
)


DEFAULT_FIGURE_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "figures"

_SCORE_COLORS = {
    "combined": "#28536b",
    "exposure": "#4f772d",
    "password": "#f4a259",
}

_ACTION_COLORS = {
    "ALLOW": "#4f772d",
    "WARN": "#f4a259",
    "REQUIRE_STRONGER_PASSWORD": "#bc4749",
    "ENFORCE_MFA": "#1d3557",
    "STEP_UP_AUTHENTICATION": "#457b9d",
    "PRIORITIZE_AWARENESS_TRAINING": "#6a4c93",
}


def aggregate_policy_rows(
    rows: list[EvaluationRunSummaryRecord],
) -> list[PolicyAggregateRecord]:
    """Aggregate flattened analysis rows into one record per policy profile."""
    grouped: dict[str, list[EvaluationRunSummaryRecord]] = {}
    for row in rows:
        grouped.setdefault(row.policy_profile.value, []).append(row)

    aggregates: list[PolicyAggregateRecord] = []
    for policy_name, group in sorted(grouped.items()):
        action_counts = Counter(row.top_action for row in group)
        run_count = len(group)
        aggregates.append(
            PolicyAggregateRecord(
                policy_profile=group[0].policy_profile,
                run_count=run_count,
                mean_combined_score=round(
                    sum(row.average_combined_score for row in group) / run_count, 2
                ),
                mean_exposure_score=round(
                    sum(row.average_exposure_score for row in group) / run_count, 2
                ),
                mean_password_score=round(
                    sum(row.average_password_score for row in group) / run_count, 2
                ),
                dominant_top_action=_most_common_action(action_counts),
                top_action_counts=dict(sorted(action_counts.items())),
            )
        )

    return aggregates


def render_policy_aggregate_table(
    aggregates: list[PolicyAggregateRecord],
) -> str:
    """Render aggregated policy metrics as a markdown table."""
    headers = (
        "Policy",
        "Runs",
        "Mean Combined",
        "Mean Exposure",
        "Mean Password",
        "Dominant Action",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for aggregate in aggregates:
        lines.append(
            "| "
            + " | ".join(
                (
                    aggregate.policy_profile.value,
                    str(aggregate.run_count),
                    f"{aggregate.mean_combined_score:.2f}",
                    f"{aggregate.mean_exposure_score:.2f}",
                    f"{aggregate.mean_password_score:.2f}",
                    aggregate.dominant_top_action,
                )
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def render_policy_aggregate_csv(
    aggregates: list[PolicyAggregateRecord],
) -> str:
    """Render aggregated policy metrics as CSV."""
    fieldnames = [
        "policy_profile",
        "run_count",
        "mean_combined_score",
        "mean_exposure_score",
        "mean_password_score",
        "dominant_top_action",
        "top_action_counts",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for aggregate in aggregates:
        row = aggregate.to_dict()
        row["top_action_counts"] = json.dumps(row["top_action_counts"], sort_keys=True)
        writer.writerow(row)
    return buffer.getvalue()


def render_policy_score_svg(
    aggregates: list[PolicyAggregateRecord],
) -> str:
    """Render grouped score bars as an SVG chart."""
    if not aggregates:
        return _empty_svg("SignalLock Policy Score Summary", "No policy aggregates available.")

    width = 960
    height = 540
    left = 90
    top = 70
    plot_width = 760
    plot_height = 320
    bottom = top + plot_height
    group_width = plot_width / len(aggregates)
    cluster_width = min(group_width * 0.68, 132)
    bar_gap = 8
    bar_width = (cluster_width - 2 * bar_gap) / 3

    elements = [
        _svg_header(width, height),
        _chart_title("SignalLock Policy Score Summary"),
        _axis_frame(left, top, plot_width, plot_height),
    ]
    elements.extend(_score_y_axis_labels(left, top, plot_height))

    for index, aggregate in enumerate(aggregates):
        group_left = left + index * group_width + (group_width - cluster_width) / 2
        values = [
            ("combined", aggregate.mean_combined_score),
            ("exposure", aggregate.mean_exposure_score),
            ("password", aggregate.mean_password_score),
        ]
        for offset, (label, value) in enumerate(values):
            bar_height = plot_height * (value / 100.0)
            x = group_left + offset * (bar_width + bar_gap)
            y = bottom - bar_height
            elements.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                f'height="{bar_height:.1f}" fill="{_SCORE_COLORS[label]}" rx="4" />'
            )
            elements.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{y - 8:.1f}" '
                'font-size="12" text-anchor="middle" fill="#22333b">'
                f"{value:.1f}</text>"
            )

        center_x = left + index * group_width + group_width / 2
        elements.append(
            f'<text x="{center_x:.1f}" y="{bottom + 28:.1f}" font-size="13" '
            'text-anchor="middle" fill="#22333b">'
            f"{_escape_xml(aggregate.policy_profile.value)}</text>"
        )

    legend_items = [
        ("Mean Combined", _SCORE_COLORS["combined"]),
        ("Mean Exposure", _SCORE_COLORS["exposure"]),
        ("Mean Password", _SCORE_COLORS["password"]),
    ]
    elements.extend(_legend(650, 88, legend_items))
    elements.append("</svg>")
    return "\n".join(elements)


def render_policy_action_svg(
    aggregates: list[PolicyAggregateRecord],
) -> str:
    """Render stacked top-action distributions as an SVG chart."""
    if not aggregates:
        return _empty_svg(
            "SignalLock Dominant Action Distribution",
            "No policy aggregates available.",
        )

    width = 960
    height = 540
    left = 90
    top = 70
    plot_width = 760
    plot_height = 320
    bottom = top + plot_height
    group_width = plot_width / len(aggregates)
    bar_width = min(group_width * 0.5, 90)
    actions = [
        action
        for action in _ACTION_COLORS
        if any(action in aggregate.top_action_counts for aggregate in aggregates)
    ]

    elements = [
        _svg_header(width, height),
        _chart_title("SignalLock Dominant Action Distribution"),
        _axis_frame(left, top, plot_width, plot_height),
    ]
    elements.extend(_percentage_y_axis_labels(left, top, plot_height))

    for index, aggregate in enumerate(aggregates):
        x = left + index * group_width + (group_width - bar_width) / 2
        current_y = bottom
        total = max(aggregate.run_count, 1)

        for action in actions:
            count = aggregate.top_action_counts.get(action, 0)
            if count == 0:
                continue
            segment_height = plot_height * (count / total)
            current_y -= segment_height
            elements.append(
                f'<rect x="{x:.1f}" y="{current_y:.1f}" width="{bar_width:.1f}" '
                f'height="{segment_height:.1f}" fill="{_ACTION_COLORS[action]}" rx="2" />'
            )

        center_x = left + index * group_width + group_width / 2
        elements.append(
            f'<text x="{center_x:.1f}" y="{bottom + 28:.1f}" font-size="13" '
            'text-anchor="middle" fill="#22333b">'
            f"{_escape_xml(aggregate.policy_profile.value)}</text>"
        )
        elements.append(
            f'<text x="{center_x:.1f}" y="{top - 10:.1f}" font-size="12" '
            'text-anchor="middle" fill="#22333b">'
            f"runs={aggregate.run_count}</text>"
        )

    legend_items = [(action, _ACTION_COLORS[action]) for action in actions]
    elements.extend(_legend(610, 82, legend_items))
    elements.append("</svg>")
    return "\n".join(elements)


def write_figure_artifacts(
    overview: EvaluationRunAnalysisOverview,
    aggregates: list[PolicyAggregateRecord],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> FigureArtifacts:
    """Persist a timestamped figure bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_FIGURE_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    summary_table = render_policy_aggregate_table(aggregates)
    aggregate_csv = render_policy_aggregate_csv(aggregates)
    score_svg = render_policy_score_svg(aggregates)
    action_svg = render_policy_action_svg(aggregates)

    summary_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "aggregates": [aggregate.to_dict() for aggregate in aggregates],
        "summary_table_markdown": summary_table,
    }

    summary_path = run_dir / "figure_summary.json"
    csv_path = run_dir / "policy_aggregates.csv"
    table_path = run_dir / "policy_summary_table.md"
    score_chart_path = run_dir / "policy_score_summary.svg"
    action_chart_path = run_dir / "policy_action_summary.svg"

    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    csv_path.write_text(aggregate_csv, encoding="utf-8")
    table_path.write_text(summary_table, encoding="utf-8")
    score_chart_path.write_text(score_svg, encoding="utf-8")
    action_chart_path.write_text(action_svg, encoding="utf-8")

    return FigureArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        aggregate_csv_file=str(csv_path.resolve()),
        summary_table_file=str(table_path.resolve()),
        score_chart_file=str(score_chart_path.resolve()),
        action_chart_file=str(action_chart_path.resolve()),
    )


def figure_results_to_json(
    overview: EvaluationRunAnalysisOverview,
    aggregates: list[PolicyAggregateRecord],
    include_aggregates: bool = False,
    pretty: bool = False,
    summary_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize figure-generation results as JSON."""
    payload: dict[str, object] = {
        "overview": overview.to_dict(),
    }
    if summary_table_markdown is not None:
        payload["summary_table_markdown"] = summary_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_aggregates:
        payload["aggregates"] = [aggregate.to_dict() for aggregate in aggregates]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _most_common_action(action_counts: Counter[str]) -> str:
    """Return a stable most-common action label."""
    if not action_counts:
        return "NONE"
    return min((-count, action) for action, count in action_counts.items())[1]


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


def _score_y_axis_labels(left: int, top: int, plot_height: int) -> list[str]:
    """Render score axis labels at 0, 25, 50, 75, and 100."""
    labels: list[str] = []
    for score in (100, 75, 50, 25, 0):
        y = top + plot_height * (1 - score / 100.0)
        labels.append(
            f'<text x="{left - 14}" y="{y + 4:.1f}" font-size="12" text-anchor="end" '
            'fill="#486581">'
            f"{score}</text>"
        )
    return labels


def _percentage_y_axis_labels(left: int, top: int, plot_height: int) -> list[str]:
    """Render percentage axis labels for stacked distributions."""
    labels: list[str] = []
    for percent in (100, 75, 50, 25, 0):
        y = top + plot_height * (1 - percent / 100.0)
        labels.append(
            f'<text x="{left - 14}" y="{y + 4:.1f}" font-size="12" text-anchor="end" '
            'fill="#486581">'
            f"{percent}%</text>"
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
