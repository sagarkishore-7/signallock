"""Offline tests for live (GitHub) collection wiring in the CLI.

No network: a fake httpx-style client is injected into the GitHub collector, so
these assert the wiring (consent gate, attribute mapping, snapshot write/merge)
without ever reaching api.github.com.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from signallock.cli import (
    _merge_observations,
    _write_snapshot,
    collect_live_observations,
)
from signallock.collect.snapshot import load_snapshot
from signallock.core import AttributeKind, SourceClass
from signallock.core.errors import ConsentError

from tests._fixtures import make_identity, make_roster

_USER = "ghostrider"


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # noqa: D401 - mimics httpx
        return None

    def json(self) -> object:
        return self._payload


class _FakeGitHubClient:
    """Returns canned GitHub user + repos payloads for the two endpoints."""

    def __init__(self, user: str, profile: dict, repos: list) -> None:
        self._user = user
        self._profile = profile
        self._repos = repos

    def get(self, url: str) -> _FakeResponse:
        if url.endswith(f"/users/{self._user}/repos"):
            return _FakeResponse(self._repos)
        if url.endswith(f"/users/{self._user}"):
            return _FakeResponse(self._profile)
        return _FakeResponse({})


class LiveCollectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = "dummy-ghost"
        self.roster = make_roster(make_identity(self.subject))
        self.client = _FakeGitHubClient(
            _USER,
            {"name": "Ghost Rider", "company": "@FabLabs", "location": "Seattle"},
            [{"language": "Python", "name": "ghost-bot", "topics": ["security"]}],
        )

    def test_collects_and_maps_github_fields(self) -> None:
        obs = collect_live_observations(
            self.subject, _USER, self.roster, client=self.client
        )
        triples = {(o.source, o.attr_kind, o.value) for o in obs}
        self.assertIn((SourceClass.CODE, AttributeKind.USERNAME, _USER), triples)
        self.assertIn((SourceClass.CODE, AttributeKind.NAME, "Ghost Rider"), triples)
        # Leading "@" on company is stripped by the collector.
        self.assertIn(
            (SourceClass.CODE, AttributeKind.ORGANIZATION, "FabLabs"), triples
        )
        self.assertIn((SourceClass.CODE, AttributeKind.LOCATION, "Seattle"), triples)
        self.assertIn((SourceClass.CODE, AttributeKind.LANGUAGE, "Python"), triples)

    def test_consent_gate_blocks_non_roster_subject(self) -> None:
        with self.assertRaises(ConsentError):
            collect_live_observations(
                "not-in-roster", _USER, self.roster, client=self.client
            )

    def test_merge_dedupes(self) -> None:
        obs = collect_live_observations(
            self.subject, _USER, self.roster, client=self.client
        )
        merged = _merge_observations(obs, obs)
        self.assertEqual(len(merged), len(obs))

    def test_write_snapshot_roundtrips(self) -> None:
        obs = collect_live_observations(
            self.subject, _USER, self.roster, client=self.client
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"{self.subject}.json"
            _write_snapshot(path, self.subject, obs)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["subject_id"], self.subject)
            reloaded = load_snapshot(path)
            self.assertEqual(len(reloaded), len(obs))
            self.assertTrue(all(o.subject_id == self.subject for o in reloaded))


if __name__ == "__main__":
    unittest.main()
