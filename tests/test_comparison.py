"""Pairwise policy-comparison tests for SignalLock."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.analysis import analyze_evaluation_runs
from signallock.comparison import (
    compare_policy_profiles,
    render_policy_comparison_csv,
    render_policy_comparison_svg,
    write_policy_comparison_artifacts,
)
from signallock.evaluation import evaluate_policy_profiles
from signallock.reporting import write_evaluation_artifacts
from signallock.schemas import PolicyProfile
from signallock.synthetic_profiles import generate_synthetic_profiles


class ComparisonTests(unittest.TestCase):
    """Validate baseline-versus-candidate policy comparison behavior."""

    def test_compare_policy_profiles_produces_summaries_and_run_deltas(self) -> None:
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
            comparison_overview, summaries, run_deltas = compare_policy_profiles(
                overview,
                rows,
                baseline_profile=PolicyProfile.BALANCED,
                candidate_profiles=[PolicyProfile.STRICT, PolicyProfile.USABILITY],
            )

            self.assertEqual(comparison_overview.total_runs_scanned, 2)
            self.assertEqual(len(summaries), 2)
            self.assertEqual(len(run_deltas), 4)
            self.assertGreaterEqual(summaries[0].matched_run_count, 2)

    def test_comparison_outputs_csv_svg_and_saved_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_run(
                temp_dir,
                seed=1,
                generated_at=datetime(2026, 5, 4, 20, 0, tzinfo=timezone.utc),
            )
            overview, rows = analyze_evaluation_runs(temp_dir)
            comparison_overview, summaries, run_deltas = compare_policy_profiles(
                overview,
                rows,
                baseline_profile=PolicyProfile.BALANCED,
                candidate_profiles=[PolicyProfile.STRICT],
            )

            csv_text = render_policy_comparison_csv(run_deltas)
            svg_text = render_policy_comparison_svg(PolicyProfile.BALANCED, summaries)
            self.assertIn("candidate_profile", csv_text)
            self.assertIn("<svg", svg_text)

            artifacts = write_policy_comparison_artifacts(
                comparison_overview,
                summaries,
                run_deltas,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 22, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(artifacts.summary_file).exists())
            self.assertTrue(Path(artifacts.run_deltas_file).exists())
            self.assertTrue(Path(artifacts.delta_chart_file).exists())

            payload = json.loads(Path(artifacts.summary_file).read_text())
            self.assertEqual(payload["overview"]["baseline_profile"], "balanced")
            self.assertEqual(len(payload["summaries"]), 1)

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
