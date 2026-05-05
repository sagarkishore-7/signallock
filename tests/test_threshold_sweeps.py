"""Threshold-sweep experiment tests for SignalLock."""

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


class ThresholdSweepTests(unittest.TestCase):
    """Validate threshold-sweep evaluation and artifact generation."""

    def test_run_threshold_sweep_returns_sorted_variants(self) -> None:
        profiles = generate_synthetic_profiles(count=3, seed=1)
        overview, records = run_threshold_sweep(
            profiles,
            base_profile=PolicyProfile.BALANCED,
            threshold_offsets=[8.0, 0.0, -8.0],
            organization="ExampleCorp",
            seed=1,
        )

        self.assertEqual(overview.variant_count, 3)
        self.assertEqual(records[0].threshold_offset, -8.0)
        self.assertEqual(records[-1].threshold_offset, 8.0)
        self.assertEqual(records[1].threshold_offset, 0.0)
        self.assertTrue(records[1].is_reference_variant)
        self.assertEqual(records[1].within_expected_range_delta, 0.0)
        self.assertEqual(records[1].false_positive_proxy_delta, 0.0)
        self.assertGreaterEqual(records[0].within_expected_range_rate, 0.0)
        self.assertLessEqual(records[0].within_expected_range_rate, 1.0)

    def test_write_threshold_sweep_artifacts_creates_bundle(self) -> None:
        profiles = generate_synthetic_profiles(count=3, seed=1)
        overview, records = run_threshold_sweep(
            profiles,
            base_profile=PolicyProfile.BALANCED,
            threshold_offsets=[-4.0, 0.0, 4.0],
            organization="ExampleCorp",
            seed=1,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = write_threshold_sweep_artifacts(
                overview,
                records,
                output_dir=temp_dir,
                generated_at=datetime(2026, 5, 5, 8, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(Path(artifacts.summary_file).exists())
            self.assertTrue(Path(artifacts.records_file).exists())
            self.assertTrue(Path(artifacts.table_file).exists())

            payload = json.loads(Path(artifacts.summary_file).read_text())
            self.assertEqual(payload["overview"]["variant_count"], 3)
            self.assertEqual(len(payload["records"]), 3)
            self.assertIn("reference_variant_label", payload["records"][0])


if __name__ == "__main__":
    unittest.main()
