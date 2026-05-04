"""Exposure normalization and scoring tests for SignalLock."""

from __future__ import annotations

import unittest

from signallock.exposure import profile_to_attribute_vector, score_exposure
from signallock.schemas import Platform, PublicProfile, RiskBand, RoleSeniority


class ExposurePipelineTests(unittest.TestCase):
    """Validate the Phase 1 exposure baseline."""

    def test_profile_to_attribute_vector_normalizes_expected_tokens(self) -> None:
        profile = PublicProfile(
            employee_id="EMP0099",
            full_name="Jane Smith",
            title="Director of Security",
            department="Security",
            organization="Example Corp",
            role_seniority=RoleSeniority.DIRECTOR,
            email_format="first.last",
            location="New York",
            tenure_start_year=2020,
            platforms=[Platform.LINKEDIN, Platform.PERSONAL_WEBSITE],
            public_usernames=["jane.smith"],
            interests=["hiking", "security research"],
            preferred_name="Janey",
            education="Georgia Tech",
            bio="Director of Security at Example Corp.",
        )

        vector = profile_to_attribute_vector(profile)

        self.assertEqual(vector.employee_id, "EMP0099")
        self.assertIn("jane", vector.name_tokens)
        self.assertIn("smith", vector.name_tokens)
        self.assertIn("janey", vector.name_tokens)
        self.assertIn("example", vector.organization_tokens)
        self.assertIn("corp", vector.organization_tokens)
        self.assertIn("security", vector.organization_tokens)
        self.assertIn("2020", vector.temporal_tokens)
        self.assertIn("jane.smith", vector.identity_tokens)
        self.assertIn("first.last", vector.identity_tokens)
        self.assertIn("new", vector.context_tokens)
        self.assertIn("york", vector.context_tokens)
        self.assertIn("georgia", vector.context_tokens)
        self.assertIn("tech", vector.context_tokens)

    def test_high_visibility_profile_scores_above_low_visibility_profile(self) -> None:
        low_profile = PublicProfile(
            employee_id="EMP0001",
            full_name="Avery Kim",
            title="Software Engineer",
            department="Engineering",
            organization="ExampleCorp",
            role_seniority=RoleSeniority.INDIVIDUAL_CONTRIBUTOR,
            email_format="first.last",
            location="Austin",
            tenure_start_year=2024,
            platforms=[Platform.LINKEDIN],
            public_usernames=["averykim"],
            interests=["running"],
        )
        high_profile = PublicProfile(
            employee_id="EMP0002",
            full_name="Priya Hughes",
            title="Chief Information Security Officer",
            department="Security",
            organization="ExampleCorp",
            role_seniority=RoleSeniority.C_SUITE,
            email_format="first.last",
            location="San Francisco",
            tenure_start_year=2018,
            platforms=[
                Platform.LINKEDIN,
                Platform.PERSONAL_WEBSITE,
                Platform.SPEAKER_BIO,
                Platform.COMPANY_DIRECTORY,
            ],
            public_usernames=["priya.hughes", "phughes"],
            interests=["security research", "writing"],
            education="MIT",
            bio="CISO at ExampleCorp and frequent public speaker.",
        )

        low_assessment = score_exposure(low_profile)
        high_assessment = score_exposure(high_profile)

        self.assertLess(low_assessment.score, high_assessment.score)
        self.assertEqual(high_assessment.band, RiskBand.CRITICAL)
        self.assertIn("seniority visibility", high_assessment.top_factors)


if __name__ == "__main__":
    unittest.main()
