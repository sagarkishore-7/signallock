"""Tests for the SignalLock explanation renderer."""

from __future__ import annotations

import json
import unittest

from signallock.explanation import (
    explain_exposure,
    explain_hardening,
    explain_password_risk,
    explain_recommendation,
    explanation_to_json,
)
from signallock.exposure import score_exposure
from signallock.password_risk import score_password_for_profile
from signallock.policy import get_policy_config, recommend_hardening
from signallock.schemas import HardeningAction, RiskBand
from signallock.synthetic_profiles import generate_synthetic_profiles


class ExposureExplanationTests(unittest.TestCase):
    """Validate exposure explanation generation."""

    def setUp(self) -> None:
        self.profiles = generate_synthetic_profiles(count=3, seed=1)
        self.profile = self.profiles[0]
        self.assessment = score_exposure(self.profile)

    def test_summary_contains_name_and_org(self) -> None:
        explanation = explain_exposure(self.assessment, self.profile)
        self.assertIn(self.profile.full_name, explanation.summary)
        self.assertIn(self.profile.organization, explanation.summary)

    def test_summary_contains_score(self) -> None:
        explanation = explain_exposure(self.assessment, self.profile)
        self.assertIn(str(int(self.assessment.score)), explanation.summary)

    def test_factor_sentences_match_top_factor_count(self) -> None:
        explanation = explain_exposure(self.assessment, self.profile)
        self.assertEqual(len(explanation.factor_sentences), len(self.assessment.top_factors))

    def test_factor_sentences_are_non_empty_strings(self) -> None:
        explanation = explain_exposure(self.assessment, self.profile)
        for sentence in explanation.factor_sentences:
            self.assertIsInstance(sentence, str)
            self.assertGreater(len(sentence), 10)

    def test_exposure_band_is_preserved(self) -> None:
        explanation = explain_exposure(self.assessment, self.profile)
        self.assertEqual(explanation.exposure_band, self.assessment.band)

    def test_serialization_round_trips(self) -> None:
        explanation = explain_exposure(self.assessment, self.profile)
        payload = explanation.to_dict()
        self.assertIn("summary", payload)
        self.assertIn("factor_sentences", payload)
        self.assertIn("exposure_band", payload)
        self.assertIsInstance(payload["exposure_band"], str)


class PasswordRiskExplanationTests(unittest.TestCase):
    """Validate password risk explanation generation."""

    def setUp(self) -> None:
        self.profiles = generate_synthetic_profiles(count=3, seed=1)
        self.profile = self.profiles[0]
        first_name = self.profile.full_name.split()[0]
        year = str(self.profile.tenure_start_year)
        self.high_risk_password = f"{first_name}{year}!"
        self.low_risk_password = "xK9#mQ2!vLpZ"

    def test_summary_contains_profile_name(self) -> None:
        assessment = score_password_for_profile(self.high_risk_password, self.profile)
        explanation = explain_password_risk(assessment, self.profile)
        self.assertIn(self.profile.full_name, explanation.summary)

    def test_high_risk_password_yields_factor_sentences(self) -> None:
        assessment = score_password_for_profile(self.high_risk_password, self.profile)
        explanation = explain_password_risk(assessment, self.profile)
        self.assertGreater(len(explanation.factor_sentences), 0)

    def test_name_overlap_sentence_references_name_tokens(self) -> None:
        assessment = score_password_for_profile(self.high_risk_password, self.profile)
        explanation = explain_password_risk(assessment, self.profile)
        sentences_text = " ".join(explanation.factor_sentences).lower()
        self.assertTrue(
            any(keyword in sentences_text for keyword in ("name", "year", "tenure", "pattern"))
        )

    def test_password_band_is_preserved(self) -> None:
        assessment = score_password_for_profile(self.high_risk_password, self.profile)
        explanation = explain_password_risk(assessment, self.profile)
        self.assertEqual(explanation.password_band, assessment.band)

    def test_serialization_round_trips(self) -> None:
        assessment = score_password_for_profile(self.high_risk_password, self.profile)
        explanation = explain_password_risk(assessment, self.profile)
        payload = explanation.to_dict()
        self.assertIn("summary", payload)
        self.assertIn("factor_sentences", payload)
        self.assertIn("password_band", payload)
        self.assertIsInstance(payload["password_band"], str)


class HardeningExplanationTests(unittest.TestCase):
    """Validate full hardening explanation generation."""

    def setUp(self) -> None:
        self.profiles = generate_synthetic_profiles(count=3, seed=1)
        self.profile = self.profiles[0]
        first_name = self.profile.full_name.split()[0]
        year = str(self.profile.tenure_start_year)
        self.password = f"{first_name}{year}!"

        self.exposure = score_exposure(self.profile)
        self.password_risk = score_password_for_profile(self.password, self.profile)
        config = get_policy_config("balanced")
        self.recommendation = recommend_hardening(self.exposure, self.password_risk, config=config)

    def test_explain_recommendation_returns_hardening_explanation(self) -> None:
        explanation = explain_recommendation(
            self.recommendation, self.profile, self.exposure, self.password_risk
        )
        self.assertEqual(explanation.employee_id, self.profile.employee_id)
        self.assertIsInstance(explanation.primary_action, HardeningAction)

    def test_action_sentence_is_non_empty(self) -> None:
        explanation = explain_recommendation(
            self.recommendation, self.profile, self.exposure, self.password_risk
        )
        self.assertGreater(len(explanation.action_sentence), 10)

    def test_full_explanation_is_multi_sentence_paragraph(self) -> None:
        explanation = explain_recommendation(
            self.recommendation, self.profile, self.exposure, self.password_risk
        )
        self.assertGreater(len(explanation.full_explanation), 80)
        self.assertIn(self.profile.full_name, explanation.full_explanation)

    def test_full_explanation_references_action(self) -> None:
        explanation = explain_recommendation(
            self.recommendation, self.profile, self.exposure, self.password_risk
        )
        self.assertIn(
            self.recommendation.primary_action.value,
            explanation.full_explanation,
        )

    def test_explain_hardening_composes_from_sub_explanations(self) -> None:
        from signallock.explanation import explain_exposure, explain_hardening, explain_password_risk

        exp_exp = explain_exposure(self.exposure, self.profile)
        pass_exp = explain_password_risk(self.password_risk, self.profile)
        result = explain_hardening(self.recommendation, exp_exp, pass_exp)

        self.assertEqual(result.exposure_explanation.employee_id, self.profile.employee_id)
        self.assertEqual(result.password_explanation.employee_id, self.profile.employee_id)

    def test_json_serialization_is_valid(self) -> None:
        explanation = explain_recommendation(
            self.recommendation, self.profile, self.exposure, self.password_risk
        )
        raw = explanation_to_json(explanation, pretty=False)
        payload = json.loads(raw)
        self.assertIn("full_explanation", payload)
        self.assertIn("exposure_explanation", payload)
        self.assertIn("password_explanation", payload)
        self.assertIn("action_sentence", payload)
        self.assertIsInstance(payload["primary_action"], str)

    def test_all_three_policy_profiles_produce_explanations(self) -> None:
        for profile_name in ("balanced", "strict", "usability"):
            config = get_policy_config(profile_name)
            rec = recommend_hardening(self.exposure, self.password_risk, config=config)
            explanation = explain_recommendation(rec, self.profile, self.exposure, self.password_risk)
            self.assertGreater(len(explanation.full_explanation), 0)
            self.assertGreater(len(explanation.action_sentence), 0)

    def test_low_risk_scenario_produces_valid_explanation(self) -> None:
        low_risk_password = "xK9#mQ2!vLpZ"
        password_risk = score_password_for_profile(low_risk_password, self.profile)
        config = get_policy_config("usability")
        recommendation = recommend_hardening(self.exposure, password_risk, config=config)
        explanation = explain_recommendation(recommendation, self.profile, self.exposure, password_risk)
        self.assertGreater(len(explanation.full_explanation), 0)
        self.assertIn(self.profile.full_name, explanation.full_explanation)


if __name__ == "__main__":
    unittest.main()
