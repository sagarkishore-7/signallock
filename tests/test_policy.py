"""Tests for the policy engine combining exposure and predictability."""

from __future__ import annotations

import unittest

from eidolon.core.enums import HardeningAction, RiskBand
from eidolon.exposure import assess_exposure
from eidolon.policy import recommend
from eidolon.predict import simulate_predictability
from eidolon.resolve import resolve_subject

from ._fixtures import SUBJECT_ID, make_identity, make_observations, make_roster


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = resolve_subject(SUBJECT_ID, make_observations())
        self.exposure = assess_exposure(self.subject)
        self.identity = make_identity()
        self.roster = make_roster(self.identity)

    def _predict(self, password: str):
        return simulate_predictability(
            self.subject, password, identity=self.identity, roster=self.roster
        )

    def test_weak_password_requires_stronger(self) -> None:
        prediction = self._predict("rex2014")
        rec = recommend(self.exposure, prediction)
        self.assertEqual(rec.primary_action, HardeningAction.REQUIRE_STRONGER_PASSWORD)
        self.assertTrue(rec.rationale)

    def test_strong_password_allows_but_exposure_adds_controls(self) -> None:
        prediction = self._predict("9f!Qz#7vLp2@Xw")
        rec = recommend(self.exposure, prediction)
        self.assertEqual(rec.predictability_band, RiskBand.LOW)
        # Primary may be ALLOW, but high exposure should still add supporting controls.
        self.assertEqual(rec.primary_action, HardeningAction.ALLOW)

    def test_combined_score_bounded_and_serializable(self) -> None:
        rec = recommend(self.exposure, self._predict("rex2014"))
        self.assertGreaterEqual(rec.combined_score, 0.0)
        self.assertLessEqual(rec.combined_score, 100.0)
        data = rec.to_dict()
        self.assertIsInstance(data["primary_action"], str)
        self.assertIsInstance(data["supporting_actions"], list)


if __name__ == "__main__":
    unittest.main()
