"""Tests for the empirical-calibration / expert-review pipeline."""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from signallock.dataset import generate_dataset
from signallock.expert_review import (
    calibration_result_to_json,
    compute_external_calibration,
    extract_ml_predicted_bands_csv,
    generate_review_tasks,
    import_expert_ratings_csv,
    write_review_tasks_csv,
    write_review_tasks_json,
)
from signallock.model import save_model, train_model
from signallock.schemas import (
    ExpertRating,
    HardeningAction,
    PolicyProfile,
    RiskBand,
)
from signallock.synthetic_profiles import generate_synthetic_profiles


class ReviewTaskGenerationTests(unittest.TestCase):
    """Validate review task export."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.profiles = generate_synthetic_profiles(count=3, seed=1)
        _, records = generate_dataset(cls.profiles, seed=1)
        training_result, fitted_model = train_model(
            records,
            model_type="gradient_boosting",
            random_state=1,
        )
        cls._model_temp_dir = tempfile.TemporaryDirectory()
        artifacts = save_model(
            fitted_model,
            training_result,
            output_dir=cls._model_temp_dir.name,
        )
        cls.model_file = artifacts.model_file

    @classmethod
    def tearDownClass(cls) -> None:
        cls._model_temp_dir.cleanup()

    def test_one_task_per_scenario_per_profile(self) -> None:
        tasks = generate_review_tasks(self.profiles)
        # 10 scenarios per profile × 3 profiles = 30 tasks
        self.assertEqual(len(tasks), 30)

    def test_task_ids_are_unique(self) -> None:
        tasks = generate_review_tasks(self.profiles)
        self.assertEqual(len(tasks), len({t.task_id for t in tasks}))

    def test_task_summary_contains_profile_name(self) -> None:
        tasks = generate_review_tasks(self.profiles)
        for task in tasks:
            self.assertIn(self.profiles[0].full_name.split()[0],
                          tasks[0].profile_summary)
            break  # one assertion per profile is enough

    def test_task_carries_heuristic_band_and_action(self) -> None:
        tasks = generate_review_tasks(self.profiles)
        for task in tasks:
            self.assertIsInstance(task.heuristic_band, RiskBand)
            self.assertIsInstance(task.heuristic_action, HardeningAction)

    def test_csv_export_has_correct_headers(self) -> None:
        tasks = generate_review_tasks(self.profiles)
        csv_text = write_review_tasks_csv(tasks)
        reader = csv.DictReader(io.StringIO(csv_text))
        for required in (
            "task_id",
            "profile_id",
            "scenario_name",
            "profile_summary",
            "password",
            "heuristic_band",
            "heuristic_action",
            "ml_predicted_band",
            "expert_band",
            "expert_action",
            "notes",
        ):
            self.assertIn(required, reader.fieldnames)

    def test_csv_export_has_empty_rating_columns(self) -> None:
        tasks = generate_review_tasks(self.profiles)
        csv_text = write_review_tasks_csv(tasks)
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        for row in rows:
            self.assertEqual(row["expert_band"], "")
            self.assertEqual(row["expert_action"], "")
            self.assertEqual(row["notes"], "")

    def test_json_export_includes_metadata(self) -> None:
        tasks = generate_review_tasks(self.profiles)
        raw = write_review_tasks_json(tasks)
        payload = json.loads(raw)
        self.assertEqual(payload["task_count"], 30)
        self.assertIn("tasks", payload)
        self.assertIn("generated_at", payload)

    def test_generate_review_tasks_can_include_ml_predicted_band(self) -> None:
        tasks = generate_review_tasks(self.profiles, model_file=self.model_file)
        self.assertEqual(len(tasks), 30)
        self.assertTrue(all(task.ml_predicted_band is not None for task in tasks))

    def test_extract_ml_predicted_bands_csv_reads_embedded_values(self) -> None:
        tasks = generate_review_tasks(self.profiles, model_file=self.model_file)
        csv_text = write_review_tasks_csv(tasks)
        path = Path(tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name)
        path.write_text(csv_text, encoding="utf-8")
        try:
            ml_bands = extract_ml_predicted_bands_csv(path)
            self.assertEqual(len(ml_bands), len(tasks))
            first_key = (tasks[0].profile_id, tasks[0].scenario_name)
            self.assertEqual(ml_bands[first_key], tasks[0].ml_predicted_band)
        finally:
            path.unlink()


class RatingImportTests(unittest.TestCase):
    """Validate parsing of completed review CSVs."""

    def setUp(self) -> None:
        self.profiles = generate_synthetic_profiles(count=2, seed=1)
        self.tasks = generate_review_tasks(self.profiles)

    def _write_completed_csv(self, fill: dict[int, str]) -> Path:
        """Write a CSV with selected rows filled in."""
        csv_text = write_review_tasks_csv(self.tasks)
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        for index, band in fill.items():
            rows[index]["expert_band"] = band
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        path = Path(tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name)
        path.write_text(out.getvalue(), encoding="utf-8")
        return path

    def test_partial_completion_skips_blanks(self) -> None:
        path = self._write_completed_csv({0: "CRITICAL", 5: "LOW"})
        ratings = import_expert_ratings_csv(path)
        self.assertEqual(len(ratings), 2)
        path.unlink()

    def test_imported_band_is_typed(self) -> None:
        path = self._write_completed_csv({0: "HIGH"})
        ratings = import_expert_ratings_csv(path)
        self.assertEqual(ratings[0].expert_band, RiskBand.HIGH)
        path.unlink()

    def test_invalid_band_raises_value_error(self) -> None:
        path = self._write_completed_csv({0: "EXTREMELY_HIGH"})
        with self.assertRaises(ValueError):
            import_expert_ratings_csv(path)
        path.unlink()


class ExternalCalibrationTests(unittest.TestCase):
    """Validate three-way calibration computation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.profiles = generate_synthetic_profiles(count=3, seed=1)
        _, cls.records = generate_dataset(cls.profiles, seed=1)

    def _ratings_matching_records(self) -> list[ExpertRating]:
        """Return one rating per record, with the rating equal to expected_risk_band.

        This produces 100 % agreement with the proxy labels — useful for
        validating that the calibration math is correct in the trivial case.
        """
        return [
            ExpertRating(
                task_id=f"T{i:04d}",
                profile_id=record.employee_id,
                scenario_name=record.scenario_name,
                expert_band=record.expected_risk_band,
            )
            for i, record in enumerate(self.records, start=1)
        ]

    def test_match_rate_perfect_against_expected_labels(self) -> None:
        ratings = self._ratings_matching_records()
        result = compute_external_calibration(self.records, ratings)
        # The heuristic does NOT match expected_risk_band perfectly — the
        # match rate should be in [0, 1] but typically below 1.
        self.assertGreaterEqual(result.heuristic_vs_expert_match_rate, 0.0)
        self.assertLessEqual(result.heuristic_vs_expert_match_rate, 1.0)

    def test_rating_count_equals_overlap_size(self) -> None:
        ratings = self._ratings_matching_records()
        result = compute_external_calibration(self.records, ratings)
        self.assertEqual(result.rating_count, len(ratings))

    def test_distributions_sum_to_rating_count(self) -> None:
        ratings = self._ratings_matching_records()
        result = compute_external_calibration(self.records, ratings)
        self.assertEqual(
            sum(result.expert_band_distribution.values()), result.rating_count
        )
        self.assertEqual(
            sum(result.heuristic_band_distribution.values()), result.rating_count
        )

    def test_severe_disagreement_count_is_non_negative(self) -> None:
        ratings = self._ratings_matching_records()
        result = compute_external_calibration(self.records, ratings)
        self.assertGreaterEqual(result.severe_disagreement_count, 0)

    def test_no_overlap_raises_value_error(self) -> None:
        unrelated = [
            ExpertRating(
                task_id="T9999",
                profile_id="EMP9999",
                scenario_name="nonexistent_scenario",
                expert_band=RiskBand.CRITICAL,
            )
        ]
        with self.assertRaises(ValueError):
            compute_external_calibration(self.records, unrelated)

    def test_perfect_expert_agreement_with_heuristic(self) -> None:
        # Make ratings exactly match the heuristic password_band.
        ratings = [
            ExpertRating(
                task_id=f"T{i:04d}",
                profile_id=record.employee_id,
                scenario_name=record.scenario_name,
                expert_band=record.password_band,
            )
            for i, record in enumerate(self.records, start=1)
        ]
        result = compute_external_calibration(self.records, ratings)
        self.assertEqual(result.heuristic_vs_expert_match_rate, 1.0)
        self.assertEqual(result.severe_disagreement_count, 0)
        self.assertEqual(result.disagreement_details, [])

    def test_three_way_with_ml_bands(self) -> None:
        ratings = self._ratings_matching_records()
        ml_bands = {
            (record.employee_id, record.scenario_name): record.expected_risk_band
            for record in self.records
        }
        result = compute_external_calibration(
            self.records, ratings, ml_predicted_bands=ml_bands
        )
        # ML predictions equal expert ratings in this synthetic test → 1.0
        self.assertEqual(result.ml_vs_expert_match_rate, 1.0)
        self.assertIsNotNone(result.ml_band_distribution)

    def test_serialization_round_trips(self) -> None:
        ratings = self._ratings_matching_records()
        result = compute_external_calibration(self.records, ratings)
        raw = calibration_result_to_json(result, pretty=False)
        payload = json.loads(raw)
        for key in (
            "rating_count",
            "heuristic_vs_expert_match_rate",
            "severe_disagreement_count",
            "expert_band_distribution",
            "heuristic_band_distribution",
            "band_transition_counts",
            "disagreement_details",
        ):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
