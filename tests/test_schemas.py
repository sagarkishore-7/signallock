"""Schema tests for SignalLock."""

from __future__ import annotations

import unittest

from signallock.schemas import Platform, PublicProfile, RoleSeniority


class PublicProfileTests(unittest.TestCase):
    """Validate core schema behavior."""

    def test_profile_normalizes_and_serializes(self) -> None:
        profile = PublicProfile(
            employee_id=" EMP0001 ",
            full_name=" Jane Smith ",
            title=" Director of Security ",
            department=" Security ",
            organization=" ExampleCorp ",
            role_seniority=RoleSeniority.DIRECTOR,
            email_format=" first.last ",
            location=" Austin ",
            tenure_start_year=2020,
            platforms=[Platform.LINKEDIN, Platform.GITHUB],
            public_usernames=[" janesmith ", "janesmith", ""],
            interests=[" hiking ", "hiking", "security research"],
        )

        self.assertEqual(profile.employee_id, "EMP0001")
        self.assertEqual(profile.full_name, "Jane Smith")
        self.assertEqual(profile.public_usernames, ["janesmith"])
        self.assertEqual(profile.interests, ["hiking", "security research"])
        self.assertEqual(profile.platform_count, 2)

        data = profile.to_dict()
        self.assertEqual(data["role_seniority"], "DIRECTOR")
        self.assertEqual(data["platforms"], ["LINKEDIN", "GITHUB"])

    def test_profile_rejects_invalid_year(self) -> None:
        with self.assertRaises(ValueError):
            PublicProfile(
                employee_id="EMP0002",
                full_name="Jane Smith",
                title="Security Engineer",
                department="Security",
                organization="ExampleCorp",
                role_seniority=RoleSeniority.INDIVIDUAL_CONTRIBUTOR,
                email_format="first.last",
                location="Austin",
                tenure_start_year=1900,
            )


if __name__ == "__main__":
    unittest.main()
