"""Reporting tests for reproducible evaluation artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from signallock.evaluation import evaluate_policy_profiles
from signallock.reporting import render_policy_comparison_table, write_evaluation_artifacts
from signallock.schemas import PolicyProfile
from signallock.synthetic_profiles import generate_synthetic_profiles


class ReportingTests(unittest.TestCase):
    """Validate evaluation reporting helpers."""

    def test_render_policy_comparison_table_outputs_markdown(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=1)
        summaries, _ = evaluate_policy_profiles(profiles, [PolicyProfile.BALANCED])

        table = render_policy_comparison_table(summaries)

        self.assertIn("| Policy | Samples | Scenarios |", table)
        self.assertIn("| balanced |", table)

    def test_write_evaluation_artifacts_creates_expected_files(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=1)
        summaries, records = evaluate_policy_profiles(profiles, [PolicyProfile.BALANCED])
        generated_at = datetime(2026, 5, 4, 20, 30, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = write_evaluation_artifacts(
                summaries,
                records,
                output_dir=temp_dir,
                include_records=True,
                metadata={"seed": 1},
                generated_at=generated_at,
            )

            self.assertEqual(artifacts.run_id, "20260504T203000Z")
            self.assertTrue(Path(artifacts.report_file).exists())
            self.assertTrue(Path(artifacts.summaries_file).exists())
            self.assertTrue(Path(artifacts.comparison_table_file).exists())
            self.assertTrue(Path(artifacts.records_file).exists())

            report_payload = json.loads(Path(artifacts.report_file).read_text())
            self.assertEqual(report_payload["metadata"]["seed"], 1)
            self.assertIn("comparison_table_markdown", report_payload)
            self.assertEqual(len(report_payload["records"]), len(records))


if __name__ == "__main__":
    unittest.main()
