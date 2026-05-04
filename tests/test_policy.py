"""Policy engine tests for SignalLock."""

from __future__ import annotations

import unittest

from signallock.exposure import score_exposure
from signallock.password_risk import score_password_for_profile
from signallock.policy import get_policy_config, recommend_hardening
from signallock.schemas import HardeningAction, Platform, PolicyProfile, PublicProfile, RoleSeniority


class PolicyTests(unittest.TestCase):
    """Validate the baseline hardening recommendation logic."""

    def test_high_context_password_triggers_stronger_password_recommendation(self) -> None:
        profile = PublicProfile(
            employee_id="EMP4001",
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
                Platform.COMPANY_DIRECTORY,
            ],
            public_usernames=["priya.hughes", "phughes"],
            interests=["security research", "writing"],
            education="MIT",
            preferred_name="Priya",
        )

        exposure = score_exposure(profile)
        password = score_password_for_profile("Priya2024!", profile)
        recommendation = recommend_hardening(exposure, password)

        self.assertEqual(recommendation.primary_action, HardeningAction.REQUIRE_STRONGER_PASSWORD)
        self.assertIn(HardeningAction.ENFORCE_MFA, recommendation.supporting_actions)
        self.assertIn(HardeningAction.PRIORITIZE_AWARENESS_TRAINING, recommendation.supporting_actions)

    def test_low_risk_case_allows_password(self) -> None:
        profile = PublicProfile(
            employee_id="EMP4002",
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

        exposure = score_exposure(profile)
        password = score_password_for_profile("R4ndom!Quantum$Lake88", profile)
        recommendation = recommend_hardening(exposure, password)

        self.assertEqual(recommendation.primary_action, HardeningAction.ALLOW)
        self.assertEqual(recommendation.supporting_actions, [])

    def test_strict_profile_escalates_more_than_usability_profile(self) -> None:
        profile = PublicProfile(
            employee_id="EMP4003",
            full_name="Priya Hughes",
            title="Director of Security",
            department="Security",
            organization="ExampleCorp",
            role_seniority=RoleSeniority.DIRECTOR,
            email_format="first.last",
            location="San Francisco",
            tenure_start_year=2024,
            platforms=[Platform.LINKEDIN, Platform.PERSONAL_WEBSITE],
            public_usernames=["priya.hughes"],
            interests=["security research", "writing"],
            preferred_name="Priya",
        )

        exposure = score_exposure(profile)
        password = score_password_for_profile("Priya2024!", profile)
        strict = recommend_hardening(exposure, password, config=get_policy_config(PolicyProfile.STRICT))
        usability = recommend_hardening(
            exposure,
            password,
            config=get_policy_config(PolicyProfile.USABILITY),
        )

        self.assertEqual(strict.policy_profile, PolicyProfile.STRICT)
        self.assertEqual(usability.policy_profile, PolicyProfile.USABILITY)
        self.assertEqual(strict.primary_action, HardeningAction.REQUIRE_STRONGER_PASSWORD)
        self.assertIn(
            usability.primary_action,
            {HardeningAction.WARN, HardeningAction.STEP_UP_AUTHENTICATION},
        )


if __name__ == "__main__":
    unittest.main()
