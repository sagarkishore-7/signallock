"""Tests for the CLI entrypoint against the example fixtures."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from eidolon.cli import main


def _run(args: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


class CliTests(unittest.TestCase):
    def test_mirror_table(self) -> None:
        code, out = _run(["mirror-table"])
        self.assertEqual(code, 0)
        table = json.loads(out)
        mirrors = {row["mirrors"] for row in table}
        self.assertIn("maigret", mirrors)
        self.assertIn("hibp", mirrors)

    def test_compare_baseline_twin_separation(self) -> None:
        # The OSINT-linked twin is flagged; the structural twin is not.
        _, out_linked = _run(
            ["compare-baseline", "--subject", "dummy-ghost", "--password", "rex2014"]
        )
        _, out_control = _run(
            ["compare-baseline", "--subject", "dummy-ghost", "--password", "fox2014"]
        )
        linked = json.loads(out_linked)
        control = json.loads(out_control)
        self.assertIsNotNone(linked["matched_category"])
        self.assertIsNone(control["matched_category"])

    def test_score_exposure_only(self) -> None:
        code, out = _run(["score", "--subject", "dummy-ghost"])
        self.assertEqual(code, 0)
        self.assertIn("exposure", json.loads(out))

    def test_missing_subject_returns_error_code(self) -> None:
        code, _ = _run(["score", "--subject", "does-not-exist"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
