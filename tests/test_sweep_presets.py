"""Tests for preset-driven multi-seed threshold-sweep orchestration."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.sweep_presets import (
    execute_sweep_preset,
    get_sweep_preset,
    load_sweep_presets,
    sweep_preset_execution_to_json,
)


class SweepPresetLoadTests(unittest.TestCase):
    """Validate default sweep preset loading."""

    def test_default_sweep_presets_load(self) -> None:
        presets = load_sweep_presets()

        self.assertGreaterEqual(len(presets), 3)
        names = {preset.name for preset in presets}
        self.assertIn("balanced_sweep", names)
        self.assertIn("all_profiles_sweep", names)
        self.assertIn("fine_sweep", names)

    def test_preset_fields_are_populated(self) -> None:
        presets = load_sweep_presets()
        for preset in presets:
            self.assertTrue(preset.name)
            self.assertTrue(preset.description)
            self.assertTrue(preset.organization)
            self.assertGreater(preset.profile_count, 0)
            self.assertTrue(preset.seeds)
            self.assertTrue(preset.base_profiles)
            self.assertTrue(preset.threshold_offsets)

    def test_custom_preset_file_loads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = _write_sweep_preset_file(temp_dir)
            presets = load_sweep_presets(preset_file=preset_file)

            self.assertEqual(len(presets), 1)
            self.assertEqual(presets[0].name, "mini_sweep")

    def test_get_sweep_preset_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = _write_sweep_preset_file(temp_dir)
            preset = get_sweep_preset("mini_sweep", preset_file=preset_file)

            self.assertEqual(preset.name, "mini_sweep")
            self.assertEqual(len(preset.seeds), 2)
            self.assertEqual(len(preset.base_profiles), 1)
            self.assertEqual(preset.base_profiles[0].value, "balanced")

    def test_get_sweep_preset_raises_for_unknown_name(self) -> None:
        with self.assertRaises(KeyError):
            get_sweep_preset("does_not_exist")


class SweepPresetExecutionTests(unittest.TestCase):
    """Validate end-to-end sweep preset execution."""

    def test_execute_creates_full_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = _write_sweep_preset_file(temp_dir)
            preset = get_sweep_preset("mini_sweep", preset_file=preset_file)
            summary = execute_sweep_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
            )

            # 2 seeds × 1 base profile = 2 sweep runs
            self.assertEqual(summary.sweep_run_count, 2)
            self.assertEqual(summary.preset_name, "mini_sweep")

    def test_execute_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = _write_sweep_preset_file(temp_dir)
            preset = get_sweep_preset("mini_sweep", preset_file=preset_file)
            summary = execute_sweep_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
            )

            manifest_path = Path(summary.preset_artifacts["manifest_file"])
            self.assertTrue(manifest_path.exists())
            payload = json.loads(manifest_path.read_text())
            self.assertEqual(payload["preset_name"], "mini_sweep")
            self.assertEqual(payload["sweep_run_count"], 2)

    def test_execute_writes_analysis_and_figures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = _write_sweep_preset_file(temp_dir)
            preset = get_sweep_preset("mini_sweep", preset_file=preset_file)
            summary = execute_sweep_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(summary.analysis_artifacts["summary_file"]).exists())
            self.assertTrue(Path(summary.figure_artifacts["summary_file"]).exists())
            self.assertTrue(Path(summary.figure_artifacts["within_range_chart_file"]).exists())
            self.assertTrue(
                Path(summary.figure_artifacts["false_positive_chart_file"]).exists()
            )

    def test_execute_multi_profile_sweep_run_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = _write_multi_profile_preset_file(temp_dir)
            preset = get_sweep_preset("multi_profile_mini", preset_file=preset_file)
            summary = execute_sweep_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 11, 0, tzinfo=timezone.utc),
            )

            # 2 seeds × 2 base profiles = 4 sweep runs
            self.assertEqual(summary.sweep_run_count, 4)

    def test_serialization_is_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = _write_sweep_preset_file(temp_dir)
            preset = get_sweep_preset("mini_sweep", preset_file=preset_file)
            summary = execute_sweep_preset(
                preset,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
            )

            raw = sweep_preset_execution_to_json(summary, pretty=False)
            payload = json.loads(raw)
            self.assertEqual(payload["preset_name"], "mini_sweep")
            self.assertIn("analysis_artifacts", payload)
            self.assertIn("figure_artifacts", payload)


def _write_sweep_preset_file(temp_dir: str) -> Path:
    payload = {
        "sweep_presets": [
            {
                "name": "mini_sweep",
                "description": "Minimal sweep preset for automated test coverage.",
                "organization": "ExampleCorp",
                "profile_count": 2,
                "seeds": [1, 2],
                "base_profiles": ["balanced"],
                "threshold_offsets": [-4.0, 0.0, 4.0],
            }
        ]
    }
    path = Path(temp_dir) / "sweep_presets.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_multi_profile_preset_file(temp_dir: str) -> Path:
    payload = {
        "sweep_presets": [
            {
                "name": "multi_profile_mini",
                "description": "Multi-profile minimal sweep for test coverage.",
                "organization": "ExampleCorp",
                "profile_count": 2,
                "seeds": [1, 2],
                "base_profiles": ["balanced", "strict"],
                "threshold_offsets": [-4.0, 0.0, 4.0],
            }
        ]
    }
    path = Path(temp_dir) / "sweep_presets_multi.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
