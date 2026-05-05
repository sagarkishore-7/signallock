"""Figure generation for SignalLock threshold-sweep analysis outputs."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .analysis import _create_unique_run_directory
from .figures import (
    _axis_frame,
    _chart_title,
    _empty_svg,
    _escape_xml,
    _legend,
    _percentage_y_axis_labels,
    _svg_header,
)
from .reporting import normalize_artifact_path
from .schemas import (
    ThresholdSweepAggregateRecord,
    ThresholdSweepAnalysisOverview,
    ThresholdSweepFigureArtifacts,
)
from .threshold_sweep_analysis import render_threshold_sweep_aggregate_csv


DEFAULT_THRESHOLD_SWEEP_FIGURE_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "threshold_sweep_figures"
)

_PROFILE_COLORS = {
    "balanced": "#28536b",
    "strict": "#bc4749",
    "usability": "#4f772d",
}


def render_threshold_sweep_within_range_svg(
    aggregates: list[ThresholdSweepAggregateRecord],
) -> str:
    """Render within-range rate by threshold offset for each base profile."""
    return _render_threshold_sweep_metric_svg(
        aggregates,
        metric_attr="mean_within_expected_range_rate",
        title="Threshold Sweep Within-Range Rate",
        subtitle="Higher is better across applied threshold offsets.",
    )


def render_threshold_sweep_false_positive_svg(
    aggregates: list[ThresholdSweepAggregateRecord],
) -> str:
    """Render false-positive proxy rate by threshold offset for each base profile."""
    return _render_threshold_sweep_metric_svg(
        aggregates,
        metric_attr="mean_false_positive_proxy_rate",
        title="Threshold Sweep False-Positive Proxy Rate",
        subtitle="Lower is better across applied threshold offsets.",
    )


def render_threshold_sweep_action_change_svg(
    aggregates: list[ThresholdSweepAggregateRecord],
) -> str:
    """Render action-change rate by threshold offset for each base profile."""
    return _render_threshold_sweep_metric_svg(
        aggregates,
        metric_attr="top_action_change_rate",
        title="Threshold Sweep Action-Change Rate",
        subtitle="Share of runs where the top action changed from the reference variant.",
    )


def write_threshold_sweep_figure_artifacts(
    overview: ThresholdSweepAnalysisOverview,
    aggregates: list[ThresholdSweepAggregateRecord],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
    summary_table_markdown: str | None = None,
) -> ThresholdSweepFigureArtifacts:
    """Persist a timestamped threshold-sweep figure bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_THRESHOLD_SWEEP_FIGURE_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    aggregate_csv = render_threshold_sweep_aggregate_csv(aggregates)
    table_markdown = summary_table_markdown or ""
    within_svg = render_threshold_sweep_within_range_svg(aggregates)
    false_positive_svg = render_threshold_sweep_false_positive_svg(aggregates)
    action_change_svg = render_threshold_sweep_action_change_svg(aggregates)

    summary_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
        "aggregates": [aggregate.to_dict() for aggregate in aggregates],
        "summary_table_markdown": table_markdown,
    }

    summary_path = run_dir / "threshold_sweep_figure_summary.json"
    aggregate_csv_path = run_dir / "threshold_sweep_aggregates.csv"
    table_path = run_dir / "threshold_sweep_summary_table.md"
    within_chart_path = run_dir / "threshold_sweep_within_range.svg"
    false_positive_chart_path = run_dir / "threshold_sweep_false_positive.svg"
    action_change_chart_path = run_dir / "threshold_sweep_action_change.svg"

    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    aggregate_csv_path.write_text(aggregate_csv, encoding="utf-8")
    table_path.write_text(table_markdown, encoding="utf-8")
    within_chart_path.write_text(within_svg, encoding="utf-8")
    false_positive_chart_path.write_text(false_positive_svg, encoding="utf-8")
    action_change_chart_path.write_text(action_change_svg, encoding="utf-8")

    return ThresholdSweepFigureArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        summary_file=str(summary_path.resolve()),
        aggregate_csv_file=str(aggregate_csv_path.resolve()),
        summary_table_file=str(table_path.resolve()),
        within_range_chart_file=str(within_chart_path.resolve()),
        false_positive_chart_file=str(false_positive_chart_path.resolve()),
        action_change_chart_file=str(action_change_chart_path.resolve()),
    )


def threshold_sweep_figure_results_to_json(
    overview: ThresholdSweepAnalysisOverview,
    aggregates: list[ThresholdSweepAggregateRecord],
    include_aggregates: bool = False,
    pretty: bool = False,
    summary_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize threshold-sweep figure-generation results as JSON."""
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


def _render_threshold_sweep_metric_svg(
    aggregates: list[ThresholdSweepAggregateRecord],
    metric_attr: str,
    title: str,
    subtitle: str,
) -> str:
    """Render one line chart over threshold offsets for all base profiles."""
    if not aggregates:
        return _empty_svg(title, "No threshold-sweep aggregates available.")

    grouped: dict[str, list[ThresholdSweepAggregateRecord]] = defaultdict(list)
    for aggregate in aggregates:
        grouped[aggregate.base_profile.value].append(aggregate)

    for group in grouped.values():
        group.sort(key=lambda record: record.threshold_offset)

    offsets = sorted({record.threshold_offset for record in aggregates})
    min_offset = min(offsets)
    max_offset = max(offsets)
    width = 960
    height = 520
    left = 90
    top = 78
    plot_width = 760
    plot_height = 300
    bottom = top + plot_height

    elements = [
        _svg_header(width, height),
        _chart_title(title),
        f'<text x="60" y="58" font-size="14" fill="#486581">{_escape_xml(subtitle)}</text>',
        _axis_frame(left, top, plot_width, plot_height),
    ]
    elements.extend(_percentage_y_axis_labels(left, top, plot_height))
    elements.extend(_offset_x_axis_labels(left, bottom, plot_width, offsets, min_offset, max_offset))

    for profile_name, group in sorted(grouped.items()):
        color = _PROFILE_COLORS.get(profile_name, "#6a4c93")
        points = [
            _line_point(
                record.threshold_offset,
                getattr(record, metric_attr),
                left,
                top,
                plot_width,
                plot_height,
                min_offset,
                max_offset,
            )
            for record in group
        ]
        if len(points) == 1:
            x, y = points[0]
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="#ffffff" stroke-width="1.5" />'
            )
        else:
            point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            elements.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{point_string}" />'
            )
            for x, y in points:
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="#ffffff" stroke-width="1.5" />'
                )

    legend_items = [
        (profile_name, _PROFILE_COLORS.get(profile_name, "#6a4c93"))
        for profile_name in sorted(grouped)
    ]
    elements.extend(_legend(650, 104, legend_items))
    elements.append("</svg>")
    return "\n".join(elements)


def _line_point(
    offset: float,
    value: float,
    left: int,
    top: int,
    plot_width: int,
    plot_height: int,
    min_offset: float,
    max_offset: float,
) -> tuple[float, float]:
    """Map one threshold offset and rate to SVG coordinates."""
    if max_offset == min_offset:
        x = left + plot_width / 2
    else:
        x = left + ((offset - min_offset) / (max_offset - min_offset)) * plot_width
    clamped = max(0.0, min(1.0, float(value)))
    y = top + (1.0 - clamped) * plot_height
    return x, y


def _offset_x_axis_labels(
    left: int,
    bottom: int,
    plot_width: int,
    offsets: list[float],
    min_offset: float,
    max_offset: float,
) -> list[str]:
    """Render threshold-offset axis labels along the x-axis."""
    labels: list[str] = []
    for offset in offsets:
        if max_offset == min_offset:
            x = left + plot_width / 2
        else:
            x = left + ((offset - min_offset) / (max_offset - min_offset)) * plot_width
        labels.append(
            f'<line x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom + 6}" '
            'stroke="#9fb3c8" stroke-width="1" />'
        )
        labels.append(
            f'<text x="{x:.1f}" y="{bottom + 24:.1f}" font-size="12" text-anchor="middle" fill="#486581">'
            f"{offset:+.0f}</text>"
        )
    labels.append(
        f'<text x="{left + plot_width / 2:.1f}" y="{bottom + 48:.1f}" font-size="13" '
        'text-anchor="middle" fill="#22333b">Threshold Offset</text>'
    )
    return labels
