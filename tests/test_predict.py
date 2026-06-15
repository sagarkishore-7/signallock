"""Tests for the predictability core: mangling, simulator, baseline, premium."""

from __future__ import annotations

import unittest

from signallock.core.enums import RiskBand
from signallock.predict import (
    context_free_strength,
    exposure_premium,
    generate_guesses,
    simulate_predictability,
)
from signallock.resolve import resolve_subject

from ._fixtures import SUBJECT_ID, make_identity, make_observations, make_roster


class ManglingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = resolve_subject(SUBJECT_ID, make_observations())

    def test_generates_personalized_affix_guess(self) -> None:
        values = {c.value for c in generate_guesses(self.subject, limit=5000)}
        self.assertIn("rex2014", values)        # pet + significant year
        self.assertIn("Rex2014", values)        # capitalized affix
        self.assertIn("rexredsox", values)      # combo

    def test_respects_limit(self) -> None:
        produced = list(generate_guesses(self.subject, limit=20))
        self.assertEqual(len(produced), 20)


class SimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = resolve_subject(SUBJECT_ID, make_observations())
        self.identity = make_identity()
        self.roster = make_roster(self.identity)

    def test_weak_contextual_password_is_cracked(self) -> None:
        result = simulate_predictability(
            self.subject, "rex2014", identity=self.identity, roster=self.roster
        )
        self.assertIsNotNone(result.reached_budget)
        self.assertIn(result.band, (RiskBand.HIGH, RiskBand.CRITICAL))
        self.assertEqual(result.matched_category, "affix")

    def test_strong_unrelated_password_survives(self) -> None:
        result = simulate_predictability(
            self.subject,
            "9f!Qz#7vLp2@Xw",
            identity=self.identity,
            roster=self.roster,
        )
        self.assertIsNone(result.reached_budget)
        self.assertEqual(result.band, RiskBand.LOW)

    def test_consent_gate_refuses_non_roster(self) -> None:
        from signallock.core import ConsentRoster, ConsentError

        with self.assertRaises(ConsentError):
            simulate_predictability(
                self.subject, "rex2014",
                identity=self.identity, roster=ConsentRoster(),
            )

    def test_output_contains_no_guess_strings(self) -> None:
        result = simulate_predictability(
            self.subject, "rex2014", identity=self.identity, roster=self.roster
        )
        serialized = str(result.to_dict())
        self.assertNotIn("rex2014", serialized)
        self.assertNotIn("rex", serialized.lower().replace("budget", ""))


class BaselineAndPremiumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = resolve_subject(SUBJECT_ID, make_observations())
        self.identity = make_identity()
        self.roster = make_roster(self.identity)

    def test_context_free_baseline_runs(self) -> None:
        strength = context_free_strength("rex2014")
        self.assertGreaterEqual(strength.zxcvbn_score, 0)
        self.assertGreater(strength.guesses_log10, 0)

    def test_exposure_premium_positive_for_osint_linked_password(self) -> None:
        # 'redsox2014' may look non-trivial to zxcvbn but is trivial in context.
        password = "redsox2014"
        baseline = context_free_strength(password)
        prediction = simulate_predictability(
            self.subject, password, identity=self.identity, roster=self.roster
        )
        premium = exposure_premium(baseline, prediction)
        if prediction.guesses_to_crack is not None:
            self.assertGreater(premium.premium, 0.0)


if __name__ == "__main__":
    unittest.main()
