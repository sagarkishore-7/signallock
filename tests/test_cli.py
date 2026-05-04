"""CLI tests for SignalLock."""

from __future__ import annotations

import contextlib
import io
import json
import unittest

from signallock.cli import main


class CLITests(unittest.TestCase):
    """Smoke-test the Phase 1 CLI workflows."""

    def test_score_exposure_outputs_json(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(["score-exposure", "--count", "2", "--seed", "3", "--pretty"])

        decoded = json.loads(stream.getvalue())
        self.assertEqual(len(decoded), 2)
        self.assertIn("score", decoded[0])
        self.assertIn("band", decoded[0])

    def test_score_password_outputs_profile_and_assessment(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(
                [
                    "score-password",
                    "--password",
                    "Priya2024!",
                    "--count",
                    "2",
                    "--seed",
                    "3",
                    "--profile-index",
                    "0",
                    "--pretty",
                ]
            )

        decoded = json.loads(stream.getvalue())
        self.assertIn("profile", decoded)
        self.assertIn("assessment", decoded)
        self.assertIn("score", decoded["assessment"])

    def test_recommend_hardening_outputs_recommendation(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(
                [
                    "recommend-hardening",
                    "--password",
                    "Priya2014!",
                    "--count",
                    "3",
                    "--seed",
                    "1",
                    "--profile-index",
                    "0",
                    "--policy-profile",
                    "strict",
                    "--pretty",
                ]
            )

        decoded = json.loads(stream.getvalue())
        self.assertIn("exposure", decoded)
        self.assertIn("password_assessment", decoded)
        self.assertIn("policy_config", decoded)
        self.assertIn("recommendation", decoded)
        self.assertIn("primary_action", decoded["recommendation"])
        self.assertEqual(decoded["recommendation"]["policy_profile"], "strict")

    def test_list_policy_profiles_outputs_json(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(["list-policy-profiles", "--pretty"])

        decoded = json.loads(stream.getvalue())
        self.assertGreaterEqual(len(decoded), 3)
        self.assertIn("profile", decoded[0])


if __name__ == "__main__":
    unittest.main()
