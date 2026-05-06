"""Tests for end-to-end ML-assisted scoring and heuristic/ML comparison."""

from __future__ import annotations

import tempfile
import unittest

try:
    import sklearn  # noqa: F401

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

from signallock.dataset import generate_dataset
from signallock.exposure import profile_to_attribute_vector, score_exposure
from signallock.model import save_model, train_model
from signallock.model_integration import compare_scoring
from signallock.password_risk import score_password_for_profile
from signallock.policy import get_policy_config, recommend_hardening
from signallock.schemas import HardeningAction, RiskBand
from signallock.synthetic_profiles import generate_synthetic_profiles


def _train_and_save(temp_dir: str, count: int = 30, seed: int = 1):
    profiles = generate_synthetic_profiles(count=count, seed=seed)
    _, records = generate_dataset(profiles, seed=seed)
    result, clf = train_model(records, random_state=42)
    artifacts = save_model(clf, result, output_dir=temp_dir)
    return artifacts.model_file


class MLAssistedPolicyTests(unittest.TestCase):
    """Validate that predicted_password_band overrides heuristic band in policy decisions."""

    def setUp(self) -> None:
        self.profiles = generate_synthetic_profiles(count=3, seed=1)
        self.profile = self.profiles[0]
        self.exposure = score_exposure(self.profile)
        self.config = get_policy_config("balanced")

    def test_heuristic_recommendation_has_ml_assisted_false(self) -> None:
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake88", self.profile)
        rec = recommend_hardening(self.exposure, password_risk, config=self.config)
        self.assertFalse(rec.ml_assisted)

    def test_ml_recommendation_has_ml_assisted_true(self) -> None:
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake88", self.profile)
        rec = recommend_hardening(
            self.exposure,
            password_risk,
            config=self.config,
            predicted_password_band=RiskBand.CRITICAL,
        )
        self.assertTrue(rec.ml_assisted)

    def test_ml_band_overrides_heuristic_band_in_output(self) -> None:
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake88", self.profile)
        rec = recommend_hardening(
            self.exposure,
            password_risk,
            config=self.config,
            predicted_password_band=RiskBand.HIGH,
        )
        self.assertEqual(rec.password_band, RiskBand.HIGH)

    def test_ml_critical_band_forces_stronger_password_action(self) -> None:
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake88", self.profile)
        heuristic_rec = recommend_hardening(self.exposure, password_risk, config=self.config)
        ml_rec = recommend_hardening(
            self.exposure,
            password_risk,
            config=self.config,
            predicted_password_band=RiskBand.CRITICAL,
        )
        self.assertEqual(ml_rec.primary_action, HardeningAction.REQUIRE_STRONGER_PASSWORD)
        self.assertNotEqual(heuristic_rec.primary_action, ml_rec.primary_action)

    def test_ml_low_band_allows_safe_password(self) -> None:
        first_name = self.profile.full_name.split()[0]
        year = str(self.profile.tenure_start_year)
        password_risk = score_password_for_profile(f"{first_name}{year}!", self.profile)
        rec = recommend_hardening(
            self.exposure,
            password_risk,
            config=self.config,
            predicted_password_band=RiskBand.LOW,
        )
        self.assertIn(rec.primary_action, (HardeningAction.ALLOW, HardeningAction.WARN))

    def test_heuristic_score_still_used_for_combined_score(self) -> None:
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake88", self.profile)
        heuristic_rec = recommend_hardening(self.exposure, password_risk, config=self.config)
        ml_rec = recommend_hardening(
            self.exposure,
            password_risk,
            config=self.config,
            predicted_password_band=RiskBand.CRITICAL,
        )
        # combined_score uses the heuristic numeric score, not the band
        self.assertEqual(heuristic_rec.combined_score, ml_rec.combined_score)

    def test_serialization_includes_ml_assisted_field(self) -> None:
        password_risk = score_password_for_profile("R4ndom!Quantum$Lake88", self.profile)
        rec = recommend_hardening(
            self.exposure,
            password_risk,
            config=self.config,
            predicted_password_band=RiskBand.HIGH,
        )
        d = rec.to_dict()
        self.assertIn("ml_assisted", d)
        self.assertTrue(d["ml_assisted"])

    def test_all_three_profiles_accept_predicted_band(self) -> None:
        password_risk = score_password_for_profile("test2019!", self.profile)
        for profile_name in ("balanced", "strict", "usability"):
            config = get_policy_config(profile_name)
            rec = recommend_hardening(
                self.exposure,
                password_risk,
                config=config,
                predicted_password_band=RiskBand.HIGH,
            )
            self.assertTrue(rec.ml_assisted)
            self.assertEqual(rec.password_band, RiskBand.HIGH)


@unittest.skipUnless(_SKLEARN_AVAILABLE, "scikit-learn not installed")
class ComparisonTests(unittest.TestCase):
    """Validate compare_scoring produces correct side-by-side outputs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory()
        cls.model_file = _train_and_save(cls._temp.name, count=30, seed=1)
        cls.profiles = generate_synthetic_profiles(count=3, seed=1)
        cls.profile = cls.profiles[0]
        cls.config = get_policy_config("balanced")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_comparison_returns_model_scoring_comparison(self) -> None:
        from signallock.schemas import ModelScoringComparison

        result = compare_scoring("R4ndom!Quantum$Lake88", self.profile, self.model_file, config=self.config)
        self.assertIsInstance(result, ModelScoringComparison)

    def test_heuristic_rec_has_ml_assisted_false(self) -> None:
        result = compare_scoring("test2019!", self.profile, self.model_file, config=self.config)
        self.assertFalse(result.heuristic_recommendation.ml_assisted)

    def test_ml_rec_has_ml_assisted_true(self) -> None:
        result = compare_scoring("test2019!", self.profile, self.model_file, config=self.config)
        self.assertTrue(result.ml_recommendation.ml_assisted)

    def test_bands_agree_field_is_consistent(self) -> None:
        result = compare_scoring("test2019!", self.profile, self.model_file, config=self.config)
        self.assertEqual(
            result.bands_agree,
            result.heuristic_password_band == result.ml_predicted_band,
        )

    def test_actions_agree_field_is_consistent(self) -> None:
        result = compare_scoring("test2019!", self.profile, self.model_file, config=self.config)
        self.assertEqual(
            result.actions_agree,
            result.heuristic_action == result.ml_action,
        )

    def test_random_strong_password_both_agree_on_low_risk(self) -> None:
        result = compare_scoring(
            "R4ndom!Quantum$Lake88",
            self.profile,
            self.model_file,
            config=self.config,
        )
        self.assertEqual(result.ml_predicted_band, RiskBand.LOW)
        self.assertTrue(result.bands_agree)
        self.assertTrue(result.actions_agree)

    def test_contextual_password_ml_escalates_above_heuristic(self) -> None:
        first_name = self.profile.full_name.split()[0]
        year = str(self.profile.tenure_start_year)
        password = f"{first_name}{year}!"
        result = compare_scoring(password, self.profile, self.model_file, config=self.config)
        self.assertIn(result.ml_predicted_band, (RiskBand.HIGH, RiskBand.CRITICAL))

    def test_serialization_round_trips(self) -> None:
        import json

        from signallock.model_integration import comparison_to_json

        result = compare_scoring("test2019!", self.profile, self.model_file, config=self.config)
        raw = comparison_to_json(result, pretty=False)
        payload = json.loads(raw)
        self.assertIn("heuristic_password_band", payload)
        self.assertIn("ml_predicted_band", payload)
        self.assertIn("bands_agree", payload)
        self.assertIn("actions_agree", payload)
        self.assertIn("heuristic_recommendation", payload)
        self.assertIn("ml_recommendation", payload)
        self.assertIn("ml_assisted", payload["ml_recommendation"])
        self.assertTrue(payload["ml_recommendation"]["ml_assisted"])
        self.assertFalse(payload["heuristic_recommendation"]["ml_assisted"])


if __name__ == "__main__":
    unittest.main()
