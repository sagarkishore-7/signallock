"""Tests for the FastAPI service, loaded against the example fixtures."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from signallock.api import create_app
from signallock.paths import get_project_root


def _client() -> TestClient:
    root = get_project_root()
    app = create_app(
        roster_path=root / "configs" / "osint_roster.example.json",
        snapshots_dir=root / "configs" / "snapshots",
    )
    return TestClient(app)


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _client()

    def test_healthz(self) -> None:
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_subjects_lists_roster(self) -> None:
        resp = self.client.get("/subjects")
        self.assertEqual(resp.status_code, 200)
        ids = {row["subject_id"] for row in resp.json()}
        self.assertIn("dummy-ghost", ids)

    def test_exposure_endpoint(self) -> None:
        resp = self.client.post("/score/exposure", json={"subject_id": "dummy-ghost"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("linkability_multiplier", resp.json())

    def test_compare_baseline_does_not_echo_password(self) -> None:
        resp = self.client.post(
            "/compare-baseline",
            json={"subject_id": "dummy-ghost", "password": "rex2014"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("premium", body)
        self.assertNotIn("rex2014", resp.text)

    def test_non_consented_subject_refused(self) -> None:
        resp = self.client.post("/score/exposure", json={"subject_id": "nobody"})
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
