"""Synthetic profile generation tests for SignalLock."""

from __future__ import annotations

import json
import unittest

from signallock.synthetic_profiles import generate_synthetic_profiles, profiles_to_json


class SyntheticProfileTests(unittest.TestCase):
    """Test synthetic profile generation behavior."""

    def test_generation_count_and_shape(self) -> None:
        profiles = generate_synthetic_profiles(count=3, organization="DemoCorp", seed=7)

        self.assertEqual(len(profiles), 3)
        self.assertEqual(profiles[0].organization, "DemoCorp")
        self.assertGreaterEqual(profiles[0].platform_count, 1)
        self.assertTrue(profiles[0].employee_id.startswith("EMP"))

    def test_generation_is_reproducible(self) -> None:
        first = generate_synthetic_profiles(count=2, seed=42)
        second = generate_synthetic_profiles(count=2, seed=42)

        self.assertEqual(
            [profile.to_dict() for profile in first],
            [profile.to_dict() for profile in second],
        )

    def test_json_serialization(self) -> None:
        profiles = generate_synthetic_profiles(count=2, seed=11)
        payload = profiles_to_json(profiles, pretty=True)
        decoded = json.loads(payload)

        self.assertEqual(len(decoded), 2)
        self.assertIn("employee_id", decoded[0])

    def test_generation_rejects_non_positive_count(self) -> None:
        with self.assertRaises(ValueError):
            generate_synthetic_profiles(count=0)


if __name__ == "__main__":
    unittest.main()
