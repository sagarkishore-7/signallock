"""Evaluation harness tests for SignalLock."""

from __future__ import annotations

import unittest

from signallock.evaluation import evaluate_policy_profiles, generate_synthetic_password_scenarios
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
        self.assertEqual(len(records), 2 * 2 * 5)
        self.assertGreaterEqual(summaries[0].scenario_count, 10)
        self.assertGreaterEqual(summaries[0].average_combined_score, 0.0)


if __name__ == "__main__":
    unittest.main()
