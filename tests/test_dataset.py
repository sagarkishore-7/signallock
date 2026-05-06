"""Tests for the SignalLock labeled dataset generator."""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from signallock.dataset import (
    dataset_results_to_json,
    dataset_to_csv,
    generate_dataset,
    write_dataset_artifacts,
)
from signallock.schemas import PolicyProfile, RiskBand
from signallock.synthetic_profiles import generate_synthetic_profiles


class DatasetGenerationTests(unittest.TestCase):
    """Validate dataset record generation and structure."""

    def setUp(self) -> None:
        self.profiles = generate_synthetic_profiles(count=3, seed=1)

    def test_record_count_equals_profiles_times_scenarios(self) -> None:
        overview, records = generate_dataset(self.profiles, seed=1)
        # 10 scenarios per profile (5 original + 5 extended)
        self.assertEqual(len(records), 3 * 10)
        self.assertEqual(overview.record_count, len(records))

    def test_overview_profile_count_matches(self) -> None:
        overview, _ = generate_dataset(self.profiles, seed=1)
        self.assertEqual(overview.profile_count, 3)

    def test_overview_scenario_count_is_ten(self) -> None:
        overview, _ = generate_dataset(self.profiles, seed=1)
        self.assertEqual(overview.scenario_count, 10)

    def test_records_contain_all_expected_fields(self) -> None:
        _, records = generate_dataset(self.profiles, seed=1)
        record = records[0]
        self.assertIsInstance(record.seniority_rank, int)
        self.assertIn(record.seniority_rank, range(5))
        self.assertIsInstance(record.exposure_score, float)
        self.assertIsInstance(record.password_score, float)
        self.assertIsInstance(record.combined_score, float)
        self.assertIsInstance(record.within_expected_range, bool)
        self.assertIsInstance(record.action_severity, int)
        self.assertIsInstance(record.expected_floor_severity, int)
        self.assertIsInstance(record.expected_ceiling_severity, int)
        self.assertIsInstance(record.action_severity_gap, int)

    def test_scores_are_in_valid_range(self) -> None:
        _, records = generate_dataset(self.profiles, seed=1)
        for record in records:
            self.assertGreaterEqual(record.exposure_score, 0.0)
            self.assertLessEqual(record.exposure_score, 100.0)
            self.assertGreaterEqual(record.password_score, 0.0)
            self.assertLessEqual(record.password_score, 100.0)
            self.assertGreaterEqual(record.combined_score, 0.0)
            self.assertLessEqual(record.combined_score, 100.0)

    def test_within_expected_range_is_consistent_with_severity(self) -> None:
        _, records = generate_dataset(self.profiles, seed=1)
        for record in records:
            within = record.expected_floor_severity <= record.action_severity <= record.expected_ceiling_severity
            self.assertEqual(record.within_expected_range, within)

    def test_action_severity_gap_is_action_minus_floor(self) -> None:
        _, records = generate_dataset(self.profiles, seed=1)
        for record in records:
            expected_gap = record.action_severity - record.expected_floor_severity
            self.assertEqual(record.action_severity_gap, expected_gap)

    def test_contextual_name_year_scenario_has_high_password_score(self) -> None:
        _, records = generate_dataset(self.profiles, seed=1)
        name_year_records = [r for r in records if r.scenario_name == "contextual_name_year"]
        self.assertGreater(len(name_year_records), 0)
        for record in name_year_records:
            self.assertGreater(record.password_score, 0.0)

    def test_random_strong_scenario_has_low_password_score(self) -> None:
        _, records = generate_dataset(self.profiles, seed=1)
        strong_records = [r for r in records if r.scenario_name == "random_strong"]
        self.assertGreater(len(strong_records), 0)
        for record in strong_records:
            self.assertLess(record.password_score, 50.0)

    def test_expected_risk_band_is_populated(self) -> None:
        _, records = generate_dataset(self.profiles, seed=1)
        bands = {record.expected_risk_band for record in records}
        self.assertIn(RiskBand.LOW, bands)
        self.assertIn(RiskBand.CRITICAL, bands)

    def test_policy_profile_is_recorded_on_each_row(self) -> None:
        _, records = generate_dataset(
            self.profiles, policy_profile=PolicyProfile.STRICT, seed=1
        )
        for record in records:
            self.assertEqual(record.policy_profile, PolicyProfile.STRICT)

    def test_within_expected_range_rate_is_between_zero_and_one(self) -> None:
        overview, _ = generate_dataset(self.profiles, seed=1)
        self.assertGreaterEqual(overview.within_expected_range_rate, 0.0)
        self.assertLessEqual(overview.within_expected_range_rate, 1.0)

    def test_risk_band_distribution_covers_all_records(self) -> None:
        overview, records = generate_dataset(self.profiles, seed=1)
        total = sum(overview.risk_band_distribution.values())
        self.assertEqual(total, len(records))

    def test_action_distribution_covers_all_records(self) -> None:
        overview, records = generate_dataset(self.profiles, seed=1)
        total = sum(overview.action_distribution.values())
        self.assertEqual(total, len(records))

    def test_generation_is_reproducible(self) -> None:
        _, records_a = generate_dataset(self.profiles, seed=1)
        _, records_b = generate_dataset(self.profiles, seed=1)
        self.assertEqual(
            [r.password_score for r in records_a],
            [r.password_score for r in records_b],
        )


class DatasetCSVTests(unittest.TestCase):
    """Validate CSV export structure."""

    def setUp(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=1)
        _, self.records = generate_dataset(profiles, seed=1)

    def test_csv_has_correct_header(self) -> None:
        csv_text = dataset_to_csv(self.records)
        reader = csv.DictReader(io.StringIO(csv_text))
        self.assertIn("employee_id", reader.fieldnames)
        self.assertIn("expected_risk_band", reader.fieldnames)
        self.assertIn("within_expected_range", reader.fieldnames)
        self.assertIn("action_severity_gap", reader.fieldnames)

    def test_csv_row_count_matches_records(self) -> None:
        csv_text = dataset_to_csv(self.records)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        self.assertEqual(len(rows), len(self.records))

    def test_csv_numeric_fields_are_parseable(self) -> None:
        csv_text = dataset_to_csv(self.records)
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            float(row["exposure_score"])
            float(row["password_score"])
            float(row["combined_score"])
            int(row["action_severity"])
            int(row["action_severity_gap"])


class DatasetArtifactTests(unittest.TestCase):
    """Validate artifact persistence."""

    def setUp(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=1)
        self.overview, self.records = generate_dataset(profiles, seed=1)

    def test_write_artifacts_creates_csv_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = write_dataset_artifacts(
                self.overview, self.records, output_dir=temp_dir
            )
            self.assertTrue(Path(artifacts.records_file).exists())
            self.assertTrue(Path(artifacts.overview_file).exists())

    def test_overview_json_contains_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = write_dataset_artifacts(
                self.overview, self.records, output_dir=temp_dir
            )
            payload = json.loads(Path(artifacts.overview_file).read_text())
            self.assertIn("overview", payload)
            self.assertIn("record_count", payload["overview"])
            self.assertIn("within_expected_range_rate", payload["overview"])

    def test_json_serialization_with_records(self) -> None:
        raw = dataset_results_to_json(
            self.overview, self.records, include_records=True, pretty=False
        )
        payload = json.loads(raw)
        self.assertIn("overview", payload)
        self.assertIn("records", payload)
        self.assertEqual(len(payload["records"]), len(self.records))

    def test_json_serialization_without_records(self) -> None:
        raw = dataset_results_to_json(
            self.overview, self.records, include_records=False, pretty=False
        )
        payload = json.loads(raw)
        self.assertIn("overview", payload)
        self.assertNotIn("records", payload)


if __name__ == "__main__":
    unittest.main()
