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


if __name__ == "__main__":
    unittest.main()
