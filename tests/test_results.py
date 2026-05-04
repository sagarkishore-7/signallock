"""Preset-results aggregation tests for SignalLock."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.presets import execute_preset, get_preset
from signallock.results import summarize_preset_runs, write_preset_results_artifacts


class PresetResultsTests(unittest.TestCase):
    """Validate aggregation across executed preset bundles."""

    def test_summarize_preset_runs_flattens_manifest_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = self._write_preset_file(temp_dir)
            preset = get_preset("mini_suite", preset_file=preset_file)
            execute_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 21, 0, tzinfo=timezone.utc),
            )

            (
                overview,
                run_records,
                policy_records,
                calibration_records,
                comparison_records,
            ) = summarize_preset_runs(input_dir=temp_dir)

            self.assertEqual(overview.preset_run_count, 1)
            self.assertEqual(len(run_records), 1)
            self.assertEqual(len(policy_records), 2)
            self.assertEqual(len(calibration_records), 2)
            self.assertEqual(len(comparison_records), 1)
            self.assertEqual(run_records[0].preset_name, "mini_suite")
            self.assertTrue(any(record.is_baseline_profile for record in policy_records))

    def test_write_preset_results_artifacts_creates_summary_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = self._write_preset_file(temp_dir)
            preset = get_preset("mini_suite", preset_file=preset_file)
            execute_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 21, 0, tzinfo=timezone.utc),
            )
            (
                overview,
                run_records,
                policy_records,
                calibration_records,
                comparison_records,
            ) = summarize_preset_runs(input_dir=temp_dir)

            artifacts = write_preset_results_artifacts(
                overview,
                run_records,
                policy_records,
                calibration_records,
                comparison_records,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 22, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(artifacts.summary_file).exists())
            self.assertTrue(Path(artifacts.preset_runs_file).exists())
            self.assertTrue(Path(artifacts.policy_summaries_file).exists())
            self.assertTrue(Path(artifacts.calibration_summaries_file).exists())
            self.assertTrue(Path(artifacts.comparison_summaries_file).exists())
            self.assertTrue(Path(artifacts.preset_table_file).exists())
            self.assertTrue(Path(artifacts.policy_table_file).exists())
            self.assertTrue(Path(artifacts.calibration_table_file).exists())
            self.assertTrue(Path(artifacts.comparison_table_file).exists())

            payload = json.loads(Path(artifacts.summary_file).read_text())
            self.assertEqual(payload["overview"]["preset_run_count"], 1)
            self.assertEqual(len(payload["policy_summaries"]), 2)
            self.assertEqual(len(payload["calibration_summaries"]), 2)

    def _write_preset_file(self, temp_dir: str) -> Path:
        payload = {
            "presets": [
                {
                    "name": "mini_suite",
                    "description": "Small preset for preset-results test coverage.",
                    "organization": "ExampleCorp",
                    "profile_count": 2,
                    "seeds": [1, 2],
                    "policy_profiles": ["balanced", "strict"],
                    "baseline_profile": "balanced",
                    "comparison_candidates": ["strict"],
                    "include_records": False,
                }
            ]
        }
        path = Path(temp_dir) / "presets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
