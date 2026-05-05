"""Figure-generation tests for SignalLock threshold-sweep outputs."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.schemas import PolicyProfile
from signallock.synthetic_profiles import generate_synthetic_profiles
from signallock.threshold_sweep_analysis import analyze_threshold_sweeps
from signallock.threshold_sweep_figures import (
    render_threshold_sweep_action_change_svg,
    render_threshold_sweep_false_positive_svg,
    render_threshold_sweep_within_range_svg,
    threshold_sweep_figure_results_to_json,
    write_threshold_sweep_figure_artifacts,
)
from signallock.threshold_sweeps import (
    run_threshold_sweep,
    write_threshold_sweep_artifacts,
)


class ThresholdSweepFigureTests(unittest.TestCase):
    """Validate aggregated threshold-sweep figure generation."""

    def test_threshold_sweep_svgs_and_json_include_expected_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_sweep(
                temp_dir,
                base_profile=PolicyProfile.BALANCED,
                seed=1,
                generated_at=datetime(2026, 5, 5, 9, 0, tzinfo=timezone.utc),
            )
            self._create_sweep(
                temp_dir,
                base_profile=PolicyProfile.STRICT,
                seed=2,
                generated_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
            )

            overview, _, aggregates = analyze_threshold_sweeps(temp_dir)
            within_svg = render_threshold_sweep_within_range_svg(aggregates)
            false_positive_svg = render_threshold_sweep_false_positive_svg(aggregates)
            action_change_svg = render_threshold_sweep_action_change_svg(aggregates)
            payload = threshold_sweep_figure_results_to_json(
                overview,
                aggregates,
                include_aggregates=True,
                summary_table_markdown="| Base | Offset |\n",
                pretty=True,
            )

            self.assertIn("<svg", within_svg)
            self.assertIn("Threshold Sweep Within-Range Rate", within_svg)
            self.assertIn("<svg", false_positive_svg)
            self.assertIn("Threshold Sweep False-Positive Proxy Rate", false_positive_svg)
            self.assertIn("<svg", action_change_svg)
            self.assertIn("Threshold Sweep Action-Change Rate", action_change_svg)
            self.assertIn('"aggregates"', payload)

    def test_write_threshold_sweep_figure_artifacts_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_sweep(
                temp_dir,
                base_profile=PolicyProfile.BALANCED,
                seed=1,
                generated_at=datetime(2026, 5, 5, 9, 0, tzinfo=timezone.utc),
            )
            overview, _, aggregates = analyze_threshold_sweeps(temp_dir)

            artifacts = write_threshold_sweep_figure_artifacts(
                overview,
                aggregates,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
                summary_table_markdown="| Base | Offset |\n",
            )

            self.assertTrue(Path(artifacts.summary_file).exists())
            self.assertTrue(Path(artifacts.aggregate_csv_file).exists())
            self.assertTrue(Path(artifacts.within_range_chart_file).exists())
            self.assertTrue(Path(artifacts.false_positive_chart_file).exists())
            self.assertTrue(Path(artifacts.action_change_chart_file).exists())

            payload = json.loads(Path(artifacts.summary_file).read_text())
            self.assertEqual(payload["overview"]["run_count"], 1)
            self.assertEqual(len(payload["aggregates"]), 3)

    def _create_sweep(
        self,
        output_dir: str,
        base_profile: PolicyProfile,
        seed: int,
        generated_at: datetime,
    ) -> None:
        profiles = generate_synthetic_profiles(count=3, seed=seed)
        overview, records = run_threshold_sweep(
            profiles,
            base_profile=base_profile,
            threshold_offsets=[-8.0, 0.0, 8.0],
            organization="ExampleCorp",
            seed=seed,
        )
        write_threshold_sweep_artifacts(
            overview,
            records,
            output_dir=output_dir,
            generated_at=generated_at,
        )


if __name__ == "__main__":
    unittest.main()
