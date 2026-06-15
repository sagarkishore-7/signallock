"""Offline, in-process tests for the attack/defense demo.

These run entirely in process — no real sockets, no third-party hosts. They build
a resolved subject from the shared fake observations (pet "rex", year "2014"),
seed the local target with the weak password "rex2014", and assert that:

  * the targeted-guess attacker cracks the weak password,
  * the loopback safety gate refuses non-loopback targets but allows 127.0.0.1,
  * the defense (re-seeding with a strong random password) defeats the attack.
"""

from __future__ import annotations

import unittest

from tests._fixtures import (
    SUBJECT_ID,
    make_identity,
    make_observations,
    make_roster,
)

from signallock.resolve import resolve_subject

try:
    from demo.run_attack import assert_loopback, run_attack
    from demo.run_defense import run_defense
    from demo.target_service import create_app

    _DEMO_AVAILABLE = True
except ImportError:  # demo extra (bcrypt/fastapi) not installed
    _DEMO_AVAILABLE = False

SEED_PASSWORD = "rex2014"


def _subject():
    return resolve_subject(SUBJECT_ID, make_observations())


@unittest.skipUnless(_DEMO_AVAILABLE, "demo extra (bcrypt) not installed")
class InProcessAttackTests(unittest.TestCase):
    def test_attack_cracks_weak_password(self) -> None:
        subject = _subject()
        app = create_app(SEED_PASSWORD)

        result = run_attack(subject=subject, app=app, in_process=True)

        self.assertTrue(result["cracked"])
        self.assertGreater(result["tries"], 0)
        self.assertIsNotNone(result["matched_category"])


@unittest.skipUnless(_DEMO_AVAILABLE, "demo extra (bcrypt) not installed")
class LoopbackGuardTests(unittest.TestCase):
    def test_rejects_non_loopback(self) -> None:
        with self.assertRaises(RuntimeError):
            assert_loopback("http://evil.example.com")

    def test_allows_loopback(self) -> None:
        # Must not raise.
        assert_loopback("http://127.0.0.1:8000")


@unittest.skipUnless(_DEMO_AVAILABLE, "demo extra (bcrypt) not installed")
class DefenseTests(unittest.TestCase):
    def test_defense_defeats_attack(self) -> None:
        subject = _subject()
        app = create_app(SEED_PASSWORD)
        identity = make_identity()
        roster = make_roster(identity)

        # Cap the budget: the weak seed is cracked well within 300 guesses and
        # the hardened password survives them, so a small budget keeps the
        # (intentionally slow) bcrypt verification loop fast in CI.
        result = run_defense(
            app=app,
            subject=subject,
            seed_password=SEED_PASSWORD,
            identity=identity,
            roster=roster,
            limit=300,
        )

        self.assertTrue(result["before"]["cracked"])
        self.assertFalse(result["after"]["cracked"])
        self.assertTrue(result["hardened"])
        self.assertIsNotNone(result["recommendation"])


if __name__ == "__main__":
    unittest.main()
