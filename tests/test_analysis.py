"""Cross-run analysis tests for saved evaluation artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.analysis import (
    analyze_evaluation_calibration_runs,
    analyze_evaluation_runs,
    render_run_calibration_csv,
    render_run_calibration_table,
    render_run_analysis_csv,
    render_run_analysis_table,
    write_run_analysis_artifacts,
)
from signallock.evaluation import evaluate_policy_profiles
from signallock.reporting import write_evaluation_artifacts
from signallock.schemas import PolicyProfile
from signallock.synthetic_profiles import generate_synthetic_profiles


class AnalysisTests(unittest.TestCase):
    """Validate aggregation across saved evaluation runs."""

    def test_analyze_evaluation_runs_flattens_multiple_runs(self) -> None:
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
            calibration_rows = analyze_evaluation_calibration_runs(temp_dir)

            self.assertEqual(overview.run_count, 2)
            self.assertEqual(overview.row_count, 6)
            self.assertEqual(overview.calibration_row_count, 6)
            self.assertIn("balanced", overview.policy_profiles)
            self.assertEqual(rows[0].organization, "ExampleCorp")
            self.assertEqual(calibration_rows[0].organization, "ExampleCorp")

    def test_analysis_outputs_table_csv_and_saved_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_run(
                temp_dir,
                seed=1,
                generated_at=datetime(2026, 5, 4, 20, 0, tzinfo=timezone.utc),
            )
            overview, rows = analyze_evaluation_runs(temp_dir, [PolicyProfile.BALANCED])
            calibration_rows = analyze_evaluation_calibration_runs(
                temp_dir,
                [PolicyProfile.BALANCED],
            )
            table = render_run_analysis_table(rows)
            csv_text = render_run_analysis_csv(rows)
            calibration_table = render_run_calibration_table(calibration_rows)
            calibration_csv = render_run_calibration_csv(calibration_rows)

            self.assertIn("| Run | Policy | Org |", table)
            self.assertIn("policy_profile", csv_text)
            self.assertIn("| Run | Policy | Within Range |", calibration_table)
            self.assertIn("within_expected_range_rate", calibration_csv)

            analysis = write_run_analysis_artifacts(
                overview,
                rows,
                calibration_rows=calibration_rows,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 22, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(analysis.analysis_file).exists())
            self.assertTrue(Path(analysis.comparison_table_file).exists())
            self.assertTrue(Path(analysis.policy_matrix_file).exists())
            self.assertTrue(Path(analysis.calibration_table_file).exists())
            self.assertTrue(Path(analysis.calibration_matrix_file).exists())

            payload = json.loads(Path(analysis.analysis_file).read_text())
            self.assertEqual(payload["overview"]["run_count"], 1)
            self.assertEqual(len(payload["rows"]), 1)
            self.assertEqual(len(payload["calibration_rows"]), 1)

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
