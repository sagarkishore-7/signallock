"""Password-risk assessment tests for SignalLock."""

from __future__ import annotations

import unittest

from signallock.password_risk import score_password_for_profile
from signallock.schemas import Platform, PublicProfile, RiskBand, RoleSeniority


class PasswordRiskTests(unittest.TestCase):
    """Validate the baseline password-risk pipeline."""

    def setUp(self) -> None:
        self.profile = PublicProfile(
            employee_id="EMP2001",
            full_name="Priya Hughes",
            title="Chief Information Security Officer",
            department="Security",
            organization="ExampleCorp",
            role_seniority=RoleSeniority.C_SUITE,
            email_format="first.last",
            location="San Francisco",
            tenure_start_year=2024,
            platforms=[
                Platform.LINKEDIN,
                Platform.PERSONAL_WEBSITE,
                Platform.SPEAKER_BIO,
            ],
            public_usernames=["priya.hughes", "phughes"],
            interests=["security research", "writing"],
            education="MIT",
            preferred_name="Priya",
        )

    def test_contextual_password_scores_higher_than_random_password(self) -> None:
        contextual = score_password_for_profile("Priya2024!", self.profile)
        random_like = score_password_for_profile("R4ndom!Quantum$Lake88", self.profile)

        self.assertGreater(contextual.score, random_like.score)
        self.assertIn("priya", contextual.matched_tokens["name_tokens"])
        self.assertIn("2024", contextual.matched_tokens["temporal_tokens"])
        self.assertIn(contextual.band, {RiskBand.HIGH, RiskBand.CRITICAL})
        self.assertEqual(random_like.band, RiskBand.LOW)

    def test_password_assessment_contains_expected_components(self) -> None:
        assessment = score_password_for_profile("ExampleCorp2024!", self.profile)

        self.assertEqual(assessment.employee_id, "EMP2001")
        self.assertIn("organization_overlap", assessment.contextual_signals)
        self.assertIn("contextual_structure", assessment.contextual_signals)
        self.assertTrue(assessment.top_factors)


if __name__ == "__main__":
    unittest.main()
