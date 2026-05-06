"""Tests for the SignalLock FastAPI service layer.

Uses fastapi.testclient.TestClient — no live server is required.
"""

from __future__ import annotations

import tempfile
import unittest

try:
    import fastapi  # noqa: F401
    from fastapi.testclient import TestClient

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

try:
    import sklearn  # noqa: F401

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

from signallock.synthetic_profiles import generate_synthetic_profiles


def _profile_payload(seed: int = 1, index: int = 0) -> dict:
    profile = generate_synthetic_profiles(count=index + 1, seed=seed)[index]
    return profile.to_dict()


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi not installed")
class HealthAndPolicyTests(unittest.TestCase):
    """Validate the open endpoints (no model required)."""

    @classmethod
    def setUpClass(cls) -> None:
        from signallock.api import create_app

        cls.client = TestClient(create_app())

    def test_healthz_reports_no_model(self) -> None:
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertFalse(body["model_loaded"])

    def test_policies_lists_three_named_profiles(self) -> None:
        response = self.client.get("/policies")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        names = {entry["profile"] for entry in body}
        self.assertEqual(names, {"balanced", "strict", "usability"})

    def test_demo_profiles_returns_synthetic_roster(self) -> None:
        response = self.client.get("/demo/profiles?count=3&seed=1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 3)
        self.assertEqual(len(body["profiles"]), 3)
        self.assertIn("employee_id", body["profiles"][0])

    def test_demo_profiles_rejects_out_of_range_count(self) -> None:
        response = self.client.get("/demo/profiles?count=500")
        self.assertEqual(response.status_code, 422)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi not installed")
class ScoringEndpointTests(unittest.TestCase):
    """Validate the scoring and recommendation endpoints in heuristic mode."""

    @classmethod
    def setUpClass(cls) -> None:
        from signallock.api import create_app

        cls.client = TestClient(create_app())
        cls.profile = _profile_payload(seed=1, index=0)

    def test_score_exposure_batch_returns_assessments(self) -> None:
        payload = {"profiles": [self.profile, _profile_payload(seed=1, index=0)]}
        response = self.client.post("/score/exposure", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["assessments"]), 2)
        self.assertIn("score", body["assessments"][0])
        self.assertIn("band", body["assessments"][0])

    def test_score_password_returns_assessment(self) -> None:
        response = self.client.post(
            "/score/password",
            json={"profile": self.profile, "password": "Priya2014!"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("score", body)
        self.assertIn("matched_tokens", body)

    def test_recommend_returns_full_recommendation(self) -> None:
        response = self.client.post(
            "/recommend",
            json={
                "profile": self.profile,
                "password": "Priya2014!",
                "policy_profile": "balanced",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("recommendation", body)
        self.assertFalse(body["recommendation"]["ml_assisted"])
        self.assertIn("primary_action", body["recommendation"])

    def test_explain_returns_paragraph(self) -> None:
        response = self.client.post(
            "/explain",
            json={
                "profile": self.profile,
                "password": "Priya2014!",
                "policy_profile": "balanced",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("full_explanation", body)
        self.assertGreater(len(body["full_explanation"]), 50)

    def test_invalid_policy_returns_422(self) -> None:
        response = self.client.post(
            "/recommend",
            json={
                "profile": self.profile,
                "password": "test",
                "policy_profile": "does_not_exist",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_role_seniority_returns_422(self) -> None:
        bad = dict(self.profile)
        bad["role_seniority"] = "BOSS"
        response = self.client.post(
            "/recommend",
            json={"profile": bad, "password": "test"},
        )
        self.assertEqual(response.status_code, 422)

    def test_recommend_with_ml_true_without_model_returns_503(self) -> None:
        response = self.client.post(
            "/recommend?ml=true",
            json={
                "profile": self.profile,
                "password": "test",
                "policy_profile": "balanced",
            },
        )
        self.assertEqual(response.status_code, 503)

    def test_compare_scoring_without_model_returns_503(self) -> None:
        response = self.client.post(
            "/compare-scoring",
            json={
                "profile": self.profile,
                "password": "test",
                "policy_profile": "balanced",
            },
        )
        self.assertEqual(response.status_code, 503)


@unittest.skipUnless(
    _FASTAPI_AVAILABLE and _SKLEARN_AVAILABLE,
    "fastapi or sklearn not installed",
)
class MLBackedAPITests(unittest.TestCase):
    """Validate ML-assisted endpoints when the server is started with --model-file."""

    @classmethod
    def setUpClass(cls) -> None:
        from signallock.api import create_app
        from signallock.dataset import generate_dataset
        from signallock.model import save_model, train_model

        cls._temp = tempfile.TemporaryDirectory()
        profiles = generate_synthetic_profiles(count=30, seed=1)
        _, records = generate_dataset(profiles, seed=1)
        result, clf = train_model(records, random_state=42)
        artifacts = save_model(clf, result, output_dir=cls._temp.name)

        cls.client = TestClient(create_app(model_file=artifacts.model_file))
        cls.profile = _profile_payload(seed=1, index=0)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_healthz_reports_model_loaded(self) -> None:
        response = self.client.get("/healthz")
        self.assertTrue(response.json()["model_loaded"])

    def test_recommend_with_ml_overrides_band(self) -> None:
        response = self.client.post(
            "/recommend?ml=true",
            json={
                "profile": self.profile,
                "password": "Priya2014!",
                "policy_profile": "balanced",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["recommendation"]["ml_assisted"])

    def test_compare_scoring_returns_full_comparison(self) -> None:
        response = self.client.post(
            "/compare-scoring",
            json={
                "profile": self.profile,
                "password": "Priya2014!",
                "policy_profile": "balanced",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        for key in (
            "heuristic_password_band",
            "ml_predicted_band",
            "bands_agree",
            "actions_agree",
            "heuristic_recommendation",
            "ml_recommendation",
        ):
            self.assertIn(key, body)
        self.assertFalse(body["heuristic_recommendation"]["ml_assisted"])
        self.assertTrue(body["ml_recommendation"]["ml_assisted"])

    def test_explain_with_ml_uses_predicted_band(self) -> None:
        response = self.client.post(
            "/explain?ml=true",
            json={
                "profile": self.profile,
                "password": "Priya2014!",
                "policy_profile": "balanced",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("full_explanation", body)
        self.assertIn("primary_action", body)


if __name__ == "__main__":
    unittest.main()
