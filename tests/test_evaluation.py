"""Evaluation harness tests for SignalLock."""

from __future__ import annotations

import unittest

from signallock.evaluation import (
    evaluate_policy_profiles,
    generate_synthetic_password_scenarios,
    summarize_policy_calibration,
)
from signallock.schemas import PolicyProfile
from signallock.synthetic_profiles import generate_synthetic_profiles


class EvaluationTests(unittest.TestCase):
    """Validate synthetic evaluation behavior."""

    def test_scenario_generation_includes_expected_keys(self) -> None:
        profile = generate_synthetic_profiles(count=1, seed=1)[0]
        scenarios = generate_synthetic_password_scenarios(profile)

        self.assertIn("contextual_name_year", scenarios)
        self.assertIn("random_strong", scenarios)
        self.assertGreaterEqual(len(scenarios), 5)

    def test_evaluate_policy_profiles_returns_summaries_and_records(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=1)
        summaries, records = evaluate_policy_profiles(
            profiles,
            [PolicyProfile.BALANCED, PolicyProfile.STRICT],
        )

        self.assertEqual(len(summaries), 2)
        self.assertEqual(len(records), 2 * 2 * 10)
        self.assertGreaterEqual(summaries[0].scenario_count, 20)
        self.assertGreaterEqual(summaries[0].average_combined_score, 0.0)
        self.assertIn("expected_risk_band", records[0].to_dict())
        self.assertIn("within_expected_range", records[0].to_dict())

    def test_summarize_policy_calibration_returns_proxy_metrics(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=1)
        _, records = evaluate_policy_profiles(
            profiles,
            [PolicyProfile.BALANCED, PolicyProfile.STRICT],
        )
        calibration = summarize_policy_calibration(
            records,
            selected_profiles=[PolicyProfile.BALANCED, PolicyProfile.STRICT],
        )

        self.assertEqual(len(calibration), 2)
        self.assertGreaterEqual(calibration[0].within_expected_range_rate, 0.0)
        self.assertLessEqual(calibration[0].within_expected_range_rate, 1.0)
        self.assertGreaterEqual(calibration[0].true_positive_proxy_rate, 0.0)
        self.assertLessEqual(calibration[0].false_positive_proxy_rate, 1.0)


if __name__ == "__main__":
    unittest.main()
