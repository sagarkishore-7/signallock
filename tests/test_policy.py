"""Policy engine tests for SignalLock."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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

    def test_policy_file_override_changes_thresholds(self) -> None:
        payload = {
            "profiles": [
                {
                    "profile": "balanced",
                    "exposure_weight": 0.1,
                    "password_weight": 0.9,
                    "warn_threshold": 95.0,
                    "step_up_threshold": 97.0,
                    "enforce_mfa_threshold": 99.0,
                    "awareness_min_exposure_band": "CRITICAL",
                    "step_up_min_exposure_band": "CRITICAL",
                    "enforce_mfa_min_exposure_band": "CRITICAL",
                    "require_stronger_min_password_band": "CRITICAL",
                    "paired_require_stronger_password_band": "CRITICAL",
                    "paired_require_stronger_min_exposure_band": "CRITICAL",
                    "warn_min_password_band": "CRITICAL"
                },
                {
                    "profile": "strict",
                    "exposure_weight": 0.45,
                    "password_weight": 0.55,
                    "warn_threshold": 32.0,
                    "step_up_threshold": 48.0,
                    "enforce_mfa_threshold": 68.0,
                    "awareness_min_exposure_band": "MEDIUM",
                    "step_up_min_exposure_band": "MEDIUM",
                    "enforce_mfa_min_exposure_band": "HIGH",
                    "require_stronger_min_password_band": "HIGH",
                    "paired_require_stronger_password_band": "MEDIUM",
                    "paired_require_stronger_min_exposure_band": "HIGH",
                    "warn_min_password_band": "MEDIUM"
                },
                {
                    "profile": "usability",
                    "exposure_weight": 0.3,
                    "password_weight": 0.7,
                    "warn_threshold": 48.0,
                    "step_up_threshold": 65.0,
                    "enforce_mfa_threshold": 82.0,
                    "awareness_min_exposure_band": "CRITICAL",
                    "step_up_min_exposure_band": "CRITICAL",
                    "enforce_mfa_min_exposure_band": "CRITICAL",
                    "require_stronger_min_password_band": "CRITICAL",
                    "paired_require_stronger_password_band": "HIGH",
                    "paired_require_stronger_min_exposure_band": "CRITICAL",
                    "warn_min_password_band": "HIGH"
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "policies.json"
            path.write_text(json.dumps(payload))
            config = get_policy_config(PolicyProfile.BALANCED, policy_file=path)

        self.assertEqual(config.warn_threshold, 95.0)
        self.assertEqual(config.exposure_weight, 0.1)


if __name__ == "__main__":
    unittest.main()
