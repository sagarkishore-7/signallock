"""Figure-generation tests for SignalLock experiment outputs."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.analysis import analyze_evaluation_runs
from signallock.evaluation import evaluate_policy_profiles
from signallock.figures import (
    aggregate_policy_rows,
    render_policy_action_svg,
    render_policy_aggregate_csv,
    render_policy_score_svg,
    write_figure_artifacts,
)
from signallock.reporting import write_evaluation_artifacts
from signallock.schemas import PolicyProfile
from signallock.synthetic_profiles import generate_synthetic_profiles


class FigureTests(unittest.TestCase):
    """Validate aggregated figure generation."""

    def test_aggregate_policy_rows_produces_one_record_per_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_run(
                temp_dir,
                seed=1,
                generated_at=datetime(2026, 5, 4, 20, 0, tzinfo=timezone.utc),
            )
            self._create_run(
                temp_dir,
                seed=2,
                generated_at=datetime(2026, 5, 4, 21, 0, tzinfo=timezone.utc),
            )
            overview, rows = analyze_evaluation_runs(temp_dir)
            aggregates = aggregate_policy_rows(rows)

            self.assertEqual(overview.run_count, 2)
            self.assertEqual(len(aggregates), 3)
            self.assertGreater(aggregates[0].run_count, 0)

    def test_svg_and_csv_generation_include_expected_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_run(
                temp_dir,
                seed=1,
                generated_at=datetime(2026, 5, 4, 20, 0, tzinfo=timezone.utc),
            )
            _, rows = analyze_evaluation_runs(temp_dir)
            aggregates = aggregate_policy_rows(rows)

            score_svg = render_policy_score_svg(aggregates)
            action_svg = render_policy_action_svg(aggregates)
            aggregate_csv = render_policy_aggregate_csv(aggregates)

            self.assertIn("<svg", score_svg)
            self.assertIn("SignalLock Policy Score Summary", score_svg)
            self.assertIn("<svg", action_svg)
            self.assertIn("balanced", aggregate_csv)

    def test_write_figure_artifacts_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_run(
                temp_dir,
                seed=1,
                generated_at=datetime(2026, 5, 4, 20, 0, tzinfo=timezone.utc),
            )
            overview, rows = analyze_evaluation_runs(temp_dir)
            aggregates = aggregate_policy_rows(rows)

            artifacts = write_figure_artifacts(
                overview,
                aggregates,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 22, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(artifacts.summary_file).exists())
            self.assertTrue(Path(artifacts.aggregate_csv_file).exists())
            self.assertTrue(Path(artifacts.score_chart_file).exists())
            self.assertTrue(Path(artifacts.action_chart_file).exists())

            payload = json.loads(Path(artifacts.summary_file).read_text())
            self.assertEqual(payload["overview"]["run_count"], 1)
            self.assertEqual(len(payload["aggregates"]), 3)

    def _create_run(self, output_dir: str, seed: int, generated_at: datetime) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=seed)
        summaries, records = evaluate_policy_profiles(
            profiles,
            [PolicyProfile.BALANCED, PolicyProfile.STRICT, PolicyProfile.USABILITY],
        )
        write_evaluation_artifacts(
            summaries,
            records,
            output_dir=output_dir,
            metadata={
                "organization": "ExampleCorp",
                "profile_count": 2,
                "seed": seed,
                "policy_profiles": ["balanced", "strict", "usability"],
                "policy_file": None,
            },
            generated_at=generated_at,
        )


if __name__ == "__main__":
    unittest.main()
