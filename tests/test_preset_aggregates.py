"""Preset aggregate analysis tests for SignalLock."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.preset_aggregates import (
    aggregate_preset_results,
    write_preset_aggregate_artifacts,
)
from signallock.presets import execute_preset, get_preset
from signallock.results import summarize_preset_runs


class PresetAggregateTests(unittest.TestCase):
    """Validate paper-style aggregate analysis over executed presets."""

    def test_aggregate_preset_results_builds_expected_groupings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = self._write_preset_file(temp_dir)
            first = get_preset("mini_strict", preset_file=preset_file)
            second = get_preset("mini_usability", preset_file=preset_file)
            execute_preset(
                first,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 21, 0, tzinfo=timezone.utc),
            )
            execute_preset(
                second,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 21, 30, tzinfo=timezone.utc),
            )

            results_overview, run_records, policy_records, comparison_records = (
                summarize_preset_runs(input_dir=temp_dir)
            )
            (
                aggregate_overview,
                preset_policy_records,
                preset_comparison_records,
                cross_policy_records,
                cross_comparison_records,
            ) = aggregate_preset_results(
                results_overview,
                run_records,
                policy_records,
                comparison_records,
            )

            self.assertEqual(aggregate_overview.preset_run_count, 2)
            self.assertEqual(len(preset_policy_records), 4)
            self.assertEqual(len(preset_comparison_records), 2)
            self.assertEqual(len(cross_policy_records), 3)
            self.assertEqual(len(cross_comparison_records), 2)
            self.assertEqual(cross_policy_records[0].preset_run_count, 2)

    def test_write_preset_aggregate_artifacts_creates_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = self._write_preset_file(temp_dir)
            first = get_preset("mini_strict", preset_file=preset_file)
            second = get_preset("mini_usability", preset_file=preset_file)
            execute_preset(
                first,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 21, 0, tzinfo=timezone.utc),
            )
            execute_preset(
                second,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 21, 30, tzinfo=timezone.utc),
            )

            results_overview, run_records, policy_records, comparison_records = (
                summarize_preset_runs(input_dir=temp_dir)
            )
            aggregates = aggregate_preset_results(
                results_overview,
                run_records,
                policy_records,
                comparison_records,
            )
            artifacts = write_preset_aggregate_artifacts(
                *aggregates,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 22, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(artifacts.summary_file).exists())
            self.assertTrue(Path(artifacts.preset_policy_csv_file).exists())
            self.assertTrue(Path(artifacts.preset_comparison_csv_file).exists())
            self.assertTrue(Path(artifacts.cross_policy_csv_file).exists())
            self.assertTrue(Path(artifacts.cross_comparison_csv_file).exists())
            self.assertTrue(Path(artifacts.preset_policy_table_file).exists())
            self.assertTrue(Path(artifacts.preset_comparison_table_file).exists())
            self.assertTrue(Path(artifacts.cross_policy_table_file).exists())
            self.assertTrue(Path(artifacts.cross_comparison_table_file).exists())

            payload = json.loads(Path(artifacts.summary_file).read_text())
            self.assertEqual(payload["overview"]["preset_run_count"], 2)
            self.assertEqual(len(payload["cross_policy_aggregates"]), 3)

    def _write_preset_file(self, temp_dir: str) -> Path:
        payload = {
            "presets": [
                {
                    "name": "mini_strict",
                    "description": "Small strict-focused preset.",
                    "organization": "ExampleCorp",
                    "profile_count": 2,
                    "seeds": [1, 2],
                    "policy_profiles": ["balanced", "strict"],
                    "baseline_profile": "balanced",
                    "comparison_candidates": ["strict"],
                    "include_records": False,
                },
                {
                    "name": "mini_usability",
                    "description": "Small usability-focused preset.",
                    "organization": "ExampleCorp",
                    "profile_count": 2,
                    "seeds": [1, 2],
                    "policy_profiles": ["balanced", "usability"],
                    "baseline_profile": "balanced",
                    "comparison_candidates": ["usability"],
                    "include_records": False,
                },
            ]
        }
        path = Path(temp_dir) / "presets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
