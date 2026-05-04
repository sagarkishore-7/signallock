"""Preset orchestration tests for SignalLock."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.presets import execute_preset, get_preset, load_presets


class PresetTests(unittest.TestCase):
    """Validate experiment preset loading and execution."""

    def test_default_presets_load(self) -> None:
        presets = load_presets()

        self.assertGreaterEqual(len(presets), 3)
        self.assertEqual(presets[0].baseline_profile.value, "balanced")

    def test_execute_preset_creates_full_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = self._write_preset_file(temp_dir)
            preset = get_preset("mini_suite", preset_file=preset_file)
            summary = execute_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 4, 20, 0, tzinfo=timezone.utc),
            )

            self.assertEqual(summary.evaluation_run_count, 2)
            self.assertTrue(Path(summary.preset_artifacts["manifest_file"]).exists())
            self.assertTrue(Path(summary.analysis_artifacts["analysis_file"]).exists())
            self.assertTrue(Path(summary.figure_artifacts["summary_file"]).exists())
            self.assertIsNotNone(summary.comparison_artifacts)
            self.assertTrue(Path(summary.comparison_artifacts["summary_file"]).exists())

            payload = json.loads(Path(summary.preset_artifacts["manifest_file"]).read_text())
            self.assertEqual(payload["preset_name"], "mini_suite")
            self.assertEqual(payload["evaluation_run_count"], 2)

    def _write_preset_file(self, temp_dir: str) -> Path:
        payload = {
            "presets": [
                {
                    "name": "mini_suite",
                    "description": "Small preset for automated test coverage.",
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
