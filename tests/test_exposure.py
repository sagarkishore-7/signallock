"""Tests for the exposure model and its linkability multiplier."""

from __future__ import annotations

import unittest

from signallock.core import AttributeKind, Observation, SourceClass
from signallock.core.enums import RiskBand
from signallock.core.subject import Subject
from signallock.exposure import assess_exposure, band_from_score
from signallock.resolve import resolve_subject

from ._fixtures import SUBJECT_ID, make_observations


class ExposureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = resolve_subject(SUBJECT_ID, make_observations())

    def test_multi_platform_subject_has_linkability_amplification(self) -> None:
        assessment = assess_exposure(self.subject)
        self.assertGreater(assessment.linkability_multiplier, 1.0)
        self.assertGreater(assessment.linkability_score, 0.0)

    def test_isolated_subject_has_no_linkability(self) -> None:
        lonely = Subject(subject_id="x")  # no platforms, no tokens
        assessment = assess_exposure(lonely)
        self.assertEqual(assessment.linkability_multiplier, 1.0)
        self.assertEqual(assessment.band, RiskBand.LOW)

    def test_disabling_axis_changes_surface(self) -> None:
        full = assess_exposure(self.subject)
        ablated = assess_exposure(
            self.subject, disabled_axes=frozenset({"personal_trivia_richness"})
        )
        self.assertNotEqual(full.base_surface, ablated.base_surface)

    def test_disabling_linkability_removes_multiplier(self) -> None:
        ablated = assess_exposure(
            self.subject, disabled_axes=frozenset({"linkability"})
        )
        self.assertEqual(ablated.linkability_multiplier, 1.0)

    def test_band_thresholds(self) -> None:
        self.assertEqual(band_from_score(80), RiskBand.CRITICAL)
        self.assertEqual(band_from_score(60), RiskBand.HIGH)
        self.assertEqual(band_from_score(30), RiskBand.MEDIUM)
        self.assertEqual(band_from_score(10), RiskBand.LOW)

    def test_score_bounded(self) -> None:
        assessment = assess_exposure(self.subject)
        self.assertGreaterEqual(assessment.score, 0.0)
        self.assertLessEqual(assessment.score, 100.0)

    def test_interests_alone_do_not_max_personal_trivia(self) -> None:
        # Many public interests (e.g. GitHub repo topics) with zero real personal
        # trivia must not max the personal-trivia axis or claim "rich personal
        # trivia". Regression for the interest-inflation bug.
        obs = [
            Observation("dev", SourceClass.CODE, AttributeKind.INTEREST,
                        f"topic{i}", 0.5, "t", "p", "github-api")
            for i in range(40)
        ]
        subject = resolve_subject("dev", obs)
        assessment = assess_exposure(subject)
        self.assertLess(assessment.axis_scores["personal_trivia_richness"], 25.0)
        self.assertNotIn(
            "Rich personal trivia exposed (pets, family, teams)",
            assessment.top_factors,
        )


if __name__ == "__main__":
    unittest.main()
