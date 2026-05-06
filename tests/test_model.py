"""Tests for the SignalLock ML model training and inference pipeline."""

from __future__ import annotations

import json
import pickle
import tempfile
import unittest
from pathlib import Path

try:
    import sklearn  # noqa: F401

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

from signallock.dataset import generate_dataset
from signallock.exposure import profile_to_attribute_vector, score_exposure
from signallock.model import (
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    extract_features,
    load_model_artifacts,
    predict_risk_band,
    save_model,
    train_model,
    train_model_cv,
    training_results_to_json,
)
from signallock.password_risk import score_password_for_profile
from signallock.schemas import RiskBand
from signallock.synthetic_profiles import generate_synthetic_profiles


def _make_records(count: int = 20, seed: int = 1):
    profiles = generate_synthetic_profiles(count=count, seed=seed)
    _, records = generate_dataset(profiles, seed=seed)
    return records


@unittest.skipUnless(_SKLEARN_AVAILABLE, "scikit-learn not installed")
class ModelTrainingTests(unittest.TestCase):
    """Validate model training, metrics, and output structure."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.records = _make_records(count=20, seed=1)

    def test_gradient_boosting_trains_without_error(self) -> None:
        result, clf = train_model(self.records, model_type="gradient_boosting")
        self.assertIsNotNone(clf)
        self.assertEqual(result.model_type, "gradient_boosting")

    def test_logistic_trains_without_error(self) -> None:
        result, clf = train_model(self.records, model_type="logistic")
        self.assertIsNotNone(clf)
        self.assertEqual(result.model_type, "logistic")

    def test_train_size_plus_test_size_equals_record_count(self) -> None:
        result, _ = train_model(self.records, test_size=0.2)
        self.assertEqual(result.train_size + result.test_size, len(self.records))

    def test_test_accuracy_is_in_valid_range(self) -> None:
        result, _ = train_model(self.records)
        self.assertGreaterEqual(result.test_accuracy, 0.0)
        self.assertLessEqual(result.test_accuracy, 1.0)

    def test_heuristic_accuracy_is_in_valid_range(self) -> None:
        result, _ = train_model(self.records)
        self.assertGreaterEqual(result.heuristic_test_accuracy, 0.0)
        self.assertLessEqual(result.heuristic_test_accuracy, 1.0)

    def test_accuracy_delta_equals_model_minus_heuristic(self) -> None:
        result, _ = train_model(self.records)
        expected_delta = round(result.test_accuracy - result.heuristic_test_accuracy, 4)
        self.assertAlmostEqual(result.accuracy_delta, expected_delta, places=4)

    def test_feature_names_match_feature_columns(self) -> None:
        result, _ = train_model(self.records)
        self.assertEqual(result.feature_names, list(FEATURE_COLUMNS))

    def test_class_labels_are_risk_band_values(self) -> None:
        result, _ = train_model(self.records)
        valid_bands = {band.value for band in RiskBand}
        for label in result.class_labels:
            self.assertIn(label, valid_bands)

    def test_gradient_boosting_has_feature_importances(self) -> None:
        result, _ = train_model(self.records, model_type="gradient_boosting")
        self.assertIsNotNone(result.feature_importances)
        self.assertEqual(set(result.feature_importances.keys()), set(FEATURE_COLUMNS))

    def test_logistic_has_coefficients(self) -> None:
        result, _ = train_model(self.records, model_type="logistic")
        self.assertIsNotNone(result.coefficients)

    def test_class_report_contains_per_class_metrics(self) -> None:
        result, _ = train_model(self.records)
        for label in result.class_labels:
            self.assertIn(label, result.class_report)

    def test_unknown_model_type_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            train_model(self.records, model_type="neural_net")

    def test_training_is_reproducible(self) -> None:
        result_a, _ = train_model(self.records, random_state=7)
        result_b, _ = train_model(self.records, random_state=7)
        self.assertEqual(result_a.test_accuracy, result_b.test_accuracy)

    def test_json_serialization_is_valid(self) -> None:
        result, _ = train_model(self.records)
        raw = training_results_to_json(result, pretty=False)
        payload = json.loads(raw)
        self.assertIn("result", payload)
        self.assertIn("test_accuracy", payload["result"])
        self.assertIn("heuristic_test_accuracy", payload["result"])
        self.assertIn("accuracy_delta", payload["result"])


@unittest.skipUnless(_SKLEARN_AVAILABLE, "scikit-learn not installed")
class ModelInferenceTests(unittest.TestCase):
    """Validate prediction on new (profile, password) pairs."""

    @classmethod
    def setUpClass(cls) -> None:
        records = _make_records(count=30, seed=2)
        _, cls.clf = train_model(records, random_state=42)
        cls.profiles = generate_synthetic_profiles(count=2, seed=99)

    def test_predict_returns_valid_risk_band(self) -> None:
        profile = self.profiles[0]
        vector = profile_to_attribute_vector(profile)
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake", profile)
        band = predict_risk_band(self.clf, vector, password_risk)
        self.assertIsInstance(band, RiskBand)

    def test_high_context_password_predicts_high_or_critical(self) -> None:
        profile = self.profiles[0]
        first_name = profile.full_name.split()[0]
        year = str(profile.tenure_start_year)
        password = f"{first_name}{year}!"
        vector = profile_to_attribute_vector(profile)
        password_risk = score_password_for_profile(password, profile)
        band = predict_risk_band(self.clf, vector, password_risk)
        self.assertIn(band, (RiskBand.HIGH, RiskBand.CRITICAL))

    def test_random_strong_password_predicts_low(self) -> None:
        profile = self.profiles[0]
        vector = profile_to_attribute_vector(profile)
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake88", profile)
        band = predict_risk_band(self.clf, vector, password_risk)
        self.assertEqual(band, RiskBand.LOW)

    def test_extract_features_returns_all_feature_columns(self) -> None:
        profile = self.profiles[0]
        vector = profile_to_attribute_vector(profile)
        password_risk = score_password_for_profile("test123", profile)
        features = extract_features(vector, password_risk)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, features)
            self.assertIsInstance(features[col], float)


@unittest.skipUnless(_SKLEARN_AVAILABLE, "scikit-learn not installed")
class ModelPersistenceTests(unittest.TestCase):
    """Validate save and load round-trip."""

    @classmethod
    def setUpClass(cls) -> None:
        records = _make_records(count=20, seed=3)
        cls.result, cls.clf = train_model(records, random_state=42)

    def test_save_creates_pkl_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = save_model(self.clf, self.result, output_dir=temp_dir)
            self.assertTrue(Path(artifacts.model_file).exists())
            self.assertTrue(Path(artifacts.metadata_file).exists())

    def test_metadata_json_contains_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = save_model(self.clf, self.result, output_dir=temp_dir)
            payload = json.loads(Path(artifacts.metadata_file).read_text())
            self.assertIn("result", payload)
            self.assertEqual(payload["result"]["model_type"], self.result.model_type)

    def test_load_round_trip_preserves_accuracy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = save_model(self.clf, self.result, output_dir=temp_dir)
            loaded_clf, loaded_result = load_model_artifacts(artifacts.model_file)
            self.assertEqual(loaded_result.test_accuracy, self.result.test_accuracy)

    def test_loaded_model_produces_same_predictions(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=55)
        profile = profiles[0]
        vector = profile_to_attribute_vector(profile)
        password_risk = score_password_for_profile("test2019!", profile)

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = save_model(self.clf, self.result, output_dir=temp_dir)
            loaded_clf, _ = load_model_artifacts(artifacts.model_file)

        band_original = predict_risk_band(self.clf, vector, password_risk)
        band_loaded = predict_risk_band(loaded_clf, vector, password_risk)
        self.assertEqual(band_original, band_loaded)

    def test_pkl_file_is_a_valid_sklearn_estimator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = save_model(self.clf, self.result, output_dir=temp_dir)
            with open(artifacts.model_file, "rb") as fh:
                loaded = pickle.load(fh)
            self.assertTrue(hasattr(loaded, "predict"))


@unittest.skipUnless(_SKLEARN_AVAILABLE, "scikit-learn not installed")
class ModelCrossValidationTests(unittest.TestCase):
    """Validate stratified k-fold cross-validation reporting."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.records = _make_records(count=30, seed=4)

    def test_cv_returns_expected_shape(self) -> None:
        result = train_model_cv(self.records, n_folds=3, model_type="gradient_boosting")
        self.assertEqual(result.n_folds, 3)
        self.assertEqual(len(result.fold_results), 3)
        self.assertEqual(result.record_count, len(self.records))

    def test_cv_accuracy_means_are_in_valid_range(self) -> None:
        result = train_model_cv(self.records, n_folds=3)
        self.assertGreaterEqual(result.model_accuracy_mean, 0.0)
        self.assertLessEqual(result.model_accuracy_mean, 1.0)
        self.assertGreaterEqual(result.heuristic_accuracy_mean, 0.0)
        self.assertLessEqual(result.heuristic_accuracy_mean, 1.0)

    def test_cv_accuracy_std_is_non_negative(self) -> None:
        result = train_model_cv(self.records, n_folds=3)
        self.assertGreaterEqual(result.model_accuracy_std, 0.0)
        self.assertGreaterEqual(result.heuristic_accuracy_std, 0.0)

    def test_cv_accuracy_delta_mean_equals_difference(self) -> None:
        result = train_model_cv(self.records, n_folds=3)
        expected = round(result.model_accuracy_mean - result.heuristic_accuracy_mean, 4)
        self.assertAlmostEqual(result.accuracy_delta_mean, expected, places=3)

    def test_cv_supports_logistic_estimator(self) -> None:
        result = train_model_cv(self.records, n_folds=3, model_type="logistic")
        self.assertEqual(result.model_type, "logistic")

    def test_cv_each_fold_reports_train_and_test_size(self) -> None:
        result = train_model_cv(self.records, n_folds=3)
        for fold in result.fold_results:
            self.assertGreater(fold["train_size"], 0)
            self.assertGreater(fold["test_size"], 0)
            self.assertEqual(
                fold["train_size"] + fold["test_size"], len(self.records)
            )

    def test_cv_accuracy_delta_per_fold(self) -> None:
        result = train_model_cv(self.records, n_folds=3)
        for fold in result.fold_results:
            expected = round(fold["model_accuracy"] - fold["heuristic_accuracy"], 4)
            self.assertAlmostEqual(fold["accuracy_delta"], expected, places=3)

    def test_cv_serialization_round_trips(self) -> None:
        result = train_model_cv(self.records, n_folds=3)
        payload = result.to_dict()
        self.assertIn("model_accuracy_mean", payload)
        self.assertIn("model_accuracy_std", payload)
        self.assertIn("heuristic_accuracy_mean", payload)
        self.assertIn("accuracy_delta_mean", payload)
        self.assertIn("fold_results", payload)
        self.assertEqual(len(payload["fold_results"]), 3)


if __name__ == "__main__":
    unittest.main()
