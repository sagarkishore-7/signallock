"""Cross-run analysis tests for saved threshold-sweep artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.schemas import PolicyProfile
from signallock.synthetic_profiles import generate_synthetic_profiles
from signallock.threshold_sweeps import (
    run_threshold_sweep,
    write_threshold_sweep_artifacts,
)
from signallock.threshold_sweep_analysis import (
    analyze_threshold_sweeps,
    render_threshold_sweep_aggregate_csv,
    render_threshold_sweep_aggregate_table,
    render_threshold_sweep_run_csv,
    render_threshold_sweep_run_table,
    write_threshold_sweep_analysis_artifacts,
)


class ThresholdSweepAnalysisTests(unittest.TestCase):
    """Validate aggregation across saved threshold-sweep bundles."""

    def test_analyze_threshold_sweeps_flattens_runs_and_aggregates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_sweep(
                temp_dir,
                base_profile=PolicyProfile.BALANCED,
                seed=1,
                generated_at=datetime(2026, 5, 5, 9, 0, tzinfo=timezone.utc),
            )
            self._create_sweep(
                temp_dir,
                base_profile=PolicyProfile.BALANCED,
                seed=2,
                generated_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
            )
            self._create_sweep(
                temp_dir,
                base_profile=PolicyProfile.STRICT,
                seed=3,
                generated_at=datetime(2026, 5, 5, 11, 0, tzinfo=timezone.utc),
            )

            overview, rows, aggregates = analyze_threshold_sweeps(temp_dir)

            self.assertEqual(overview.run_count, 3)
            self.assertEqual(overview.row_count, 9)
            self.assertEqual(overview.aggregate_count, 6)
            self.assertIn("balanced", overview.base_profiles)
            self.assertEqual(rows[0].organization, "ExampleCorp")
            balanced_zero = [
                record
                for record in aggregates
                if record.base_profile == PolicyProfile.BALANCED
                and record.threshold_offset == 0.0
            ]
            self.assertEqual(len(balanced_zero), 1)
            self.assertEqual(balanced_zero[0].run_count, 2)

    def test_analysis_outputs_tables_csv_and_saved_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_sweep(
                temp_dir,
                base_profile=PolicyProfile.BALANCED,
                seed=1,
                generated_at=datetime(2026, 5, 5, 9, 0, tzinfo=timezone.utc),
            )
            overview, rows, aggregates = analyze_threshold_sweeps(
                temp_dir,
                [PolicyProfile.BALANCED],
            )
            run_table = render_threshold_sweep_run_table(rows)
            run_csv = render_threshold_sweep_run_csv(rows)
            aggregate_table = render_threshold_sweep_aggregate_table(aggregates)
            aggregate_csv = render_threshold_sweep_aggregate_csv(aggregates)

            self.assertIn("| Run | Base | Offset |", run_table)
            self.assertIn("threshold_offset", run_csv)
            self.assertIn("| Base | Offset | Runs |", aggregate_table)
            self.assertIn("mean_false_positive_proxy_delta", aggregate_csv)

            artifacts = write_threshold_sweep_analysis_artifacts(
                overview,
                rows,
                aggregates,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(artifacts.summary_file).exists())
            self.assertTrue(Path(artifacts.rows_file).exists())
            self.assertTrue(Path(artifacts.run_table_file).exists())
            self.assertTrue(Path(artifacts.aggregate_file).exists())
            self.assertTrue(Path(artifacts.aggregate_table_file).exists())

            payload = json.loads(Path(artifacts.summary_file).read_text())
            self.assertEqual(payload["overview"]["run_count"], 1)
            self.assertEqual(len(payload["rows"]), 3)
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
