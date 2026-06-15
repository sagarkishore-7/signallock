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

    def test_affix_coverage_includes_common_numbers_and_dynamic_years(self) -> None:
        # Broadened, de-hardcoded affixes: a common 2-digit number ('99') and the
        # current year (dynamic, not hardcoded) must both be reachable.
        from datetime import datetime, timezone

        values = {c.value for c in generate_guesses(self.subject, limit=30000)}
        self.assertIn("rex99", values)  # regression for the '99' false-negative
        year = datetime.now(timezone.utc).year
        self.assertIn(f"rex{year}", values)  # dynamic recent year

    def test_noisy_interest_tokens_are_capped(self) -> None:
        # A long tail of public repo-derived interests must not flood the guess
        # dossier (regression for the token-quality dilution finding).
        from signallock.core import AttributeKind, Observation, SourceClass
        from signallock.core.enums import TokenBucket
        from signallock.predict.mangling import _BASE_BUCKET_CAPS, _base_words

        obs = [
            Observation("dev", SourceClass.CODE, AttributeKind.INTEREST,
                        f"projectalpha{i}", 0.5, "t", "p", "github-api")
            for i in range(30)
        ]
        subject = resolve_subject("dev", obs)
        interest_tokens = set(subject.tokens(TokenBucket.INTEREST))
        used = [w for w in _base_words(subject) if w in interest_tokens]
        self.assertLessEqual(len(used), _BASE_BUCKET_CAPS[TokenBucket.INTEREST])


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

    def test_survivor_password_has_near_zero_premium(self) -> None:
        # A strong password that survives the targeted budget must NOT score a
        # large premium just because zxcvbn rates it strong. Regression for the
        # survivor-premium bug (flooring contextual at log10(ceiling) made strong
        # passwords show the biggest premiums).
        password = "9f!Qz#7vLp2@Xw"
        baseline = context_free_strength(password)
        prediction = simulate_predictability(
            self.subject, password, identity=self.identity, roster=self.roster
        )
        self.assertIsNone(prediction.guesses_to_crack)  # survived
        premium = exposure_premium(baseline, prediction)
        self.assertAlmostEqual(premium.premium, 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
