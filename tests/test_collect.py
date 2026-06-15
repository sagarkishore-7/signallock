"""Tests for the adversary-mirrored collection layer — all fully offline.

No test here touches a real network: live collectors are exercised through a
small fake httpx-like client, and snapshot-backed collectors through temporary
JSON files. Only clearly-fake data is used.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from signallock.collect import (
    BreachIntel,
    CodeProfile,
    SnapshotCollector,
    adversary_mirror_table,
    load_snapshot,
)
from signallock.core.enums import AttributeKind, SourceClass
from signallock.core.errors import CollectorError, ConsentError
from signallock.core.identity import (
    ConsentRecord,
    ConsentRoster,
    ConsentedIdentity,
    IdentitySeeds,
)


def _identity(subject_id: str = "s", **seeds) -> ConsentedIdentity:
    if not seeds:
        seeds = {"username": "ghostrider"}
    return ConsentedIdentity(
        subject_id,
        IdentitySeeds(**seeds),
        ConsentRecord(subject_id, "consent-ref", "2026-06-01"),
    )


def _roster(*subject_ids: str) -> ConsentRoster:
    return ConsentRoster(
        {sid: ConsentRecord(sid, "consent-ref", "2026-06-01") for sid in subject_ids}
    )


class _FakeResponse:
    """Stand-in for an httpx.Response with the bits the collectors use."""

    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    """Maps URLs to canned responses; mimics an injected httpx.Client."""

    def __init__(self, routes: dict[str, _FakeResponse]) -> None:
        self._routes = routes

    def get(self, url: str) -> _FakeResponse:
        if url not in self._routes:
            raise AssertionError(f"unexpected URL requested: {url}")
        return self._routes[url]


_GITHUB_USER = {
    "login": "ghostrider",
    "name": "Ghost Rider",
    "company": "@AcmeCorp",
    "location": "Springfield",
}
_GITHUB_REPOS = [
    {"name": "fakeproj", "language": "Python", "topics": ["osint", "defense"]},
    {"name": "otherproj", "language": "Rust", "topics": []},
]


def _github_client() -> _FakeClient:
    return _FakeClient(
        {
            "https://api.github.com/users/ghostrider": _FakeResponse(_GITHUB_USER),
            "https://api.github.com/users/ghostrider/repos": _FakeResponse(
                _GITHUB_REPOS
            ),
        }
    )


class ConsentGateTests(unittest.TestCase):
    def test_collect_refuses_non_roster_identity(self) -> None:
        collector = CodeProfile(client=_github_client())
        identity = _identity("nope")
        empty_roster = _roster()  # subject not present
        with self.assertRaises(ConsentError):
            collector.collect(identity, roster=empty_roster)


class CodeProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity = _identity("s", username="ghostrider")
        self.roster = _roster("s")
        self.obs = CodeProfile(client=_github_client()).collect(
            self.identity, roster=self.roster
        )

    def _values(self, kind: AttributeKind) -> set[str]:
        return {o.value for o in self.obs if o.attr_kind == kind}

    def test_emits_username_org_and_languages(self) -> None:
        self.assertIn("ghostrider", self._values(AttributeKind.USERNAME))
        self.assertIn("AcmeCorp", self._values(AttributeKind.ORGANIZATION))
        languages = self._values(AttributeKind.LANGUAGE)
        self.assertIn("Python", languages)
        self.assertIn("Rust", languages)

    def test_emits_name_and_location_and_interests(self) -> None:
        self.assertIn("Ghost Rider", self._values(AttributeKind.NAME))
        self.assertIn("Springfield", self._values(AttributeKind.LOCATION))
        interests = self._values(AttributeKind.INTEREST)
        self.assertIn("fakeproj", interests)
        self.assertIn("osint", interests)

    def test_source_and_mirrors_stamped(self) -> None:
        self.assertTrue(self.obs)
        for o in self.obs:
            self.assertEqual(o.source, SourceClass.CODE)
            self.assertEqual(o.mirrors, "github-api")

    def test_http_error_raises_collector_error(self) -> None:
        client = _FakeClient(
            {
                "https://api.github.com/users/ghostrider": _FakeResponse(
                    {}, status_code=404
                )
            }
        )
        with self.assertRaises(CollectorError):
            CodeProfile(client=client).collect(self.identity, roster=self.roster)


class SnapshotTests(unittest.TestCase):
    def _write(self, payload: dict) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "snap.json"
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        return tmp

    def test_load_snapshot_roundtrips_fields_and_enums(self) -> None:
        path = self._write(
            {
                "subject_id": "s",
                "observations": [
                    {
                        "source": "SOCIAL",
                        "attr_kind": "PET_NAME",
                        "value": "Rex",
                        "confidence": 0.8,
                        "mirrors": "cupp",
                        "provenance": "snapshot:ig",
                    }
                ],
            }
        )
        obs = load_snapshot(path)
        self.assertEqual(len(obs), 1)
        o = obs[0]
        self.assertEqual(o.subject_id, "s")
        self.assertEqual(o.source, SourceClass.SOCIAL)
        self.assertEqual(o.attr_kind, AttributeKind.PET_NAME)
        self.assertEqual(o.value, "Rex")
        self.assertEqual(o.confidence, 0.8)
        self.assertEqual(o.mirrors, "cupp")
        self.assertEqual(o.provenance, "snapshot:ig")

    def test_load_snapshot_defaults_optional_fields(self) -> None:
        path = self._write(
            {
                "subject_id": "s",
                "observations": [
                    {"source": "WEB", "attr_kind": "INTEREST", "value": "chess"}
                ],
            }
        )
        o = load_snapshot(path)[0]
        self.assertEqual(o.confidence, 0.9)
        self.assertTrue(o.provenance)
        self.assertTrue(o.collected_at)

    def test_snapshot_collector_filters_by_subject(self) -> None:
        path = self._write(
            {
                "subject_id": "s",
                "observations": [
                    {"source": "WEB", "attr_kind": "INTEREST", "value": "chess"}
                ],
            }
        )
        collector = SnapshotCollector(snapshot_path=path)
        same = collector.collect(_identity("s"), roster=_roster("s"))
        self.assertEqual(len(same), 1)
        other = collector.collect(_identity("other"), roster=_roster("other"))
        self.assertEqual(other, [])


class BreachIntelTests(unittest.TestCase):
    def _snapshot_path(self) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "breach.json"
        tmp.write_text(
            json.dumps(
                {
                    "subject_id": "s",
                    "observations": [
                        {
                            "source": "BREACH_INTEL",
                            "attr_kind": "BREACH",
                            "value": "FakeBreach2019",
                            "mirrors": "hibp",
                        },
                        {
                            "source": "BREACH_INTEL",
                            "attr_kind": "STRUCTURE_PRIOR",
                            "value": "word+4digits",
                            "mirrors": "hibp",
                        },
                        # An operator mistake: a non-allowed kind must be dropped.
                        {
                            "source": "BREACH_INTEL",
                            "attr_kind": "USERNAME",
                            "value": "should-not-leak",
                            "mirrors": "hibp",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return tmp

    def test_live_path_raises(self) -> None:
        with self.assertRaises(CollectorError):
            BreachIntel(live=True).collect(_identity("s"), roster=_roster("s"))

    def test_snapshot_emits_only_breach_and_structure_prior(self) -> None:
        obs = BreachIntel(snapshot_path=self._snapshot_path()).collect(
            _identity("s"), roster=_roster("s")
        )
        kinds = {o.attr_kind for o in obs}
        self.assertEqual(
            kinds, {AttributeKind.BREACH, AttributeKind.STRUCTURE_PRIOR}
        )
        # No cleartext / non-allowed field leaks through.
        self.assertNotIn(
            "should-not-leak", {o.value for o in obs}
        )


class MirrorTableTests(unittest.TestCase):
    def test_table_includes_expected_attacker_tools(self) -> None:
        mirrors = {row["mirrors"] for row in adversary_mirror_table()}
        for expected in ("maigret", "holehe", "hibp", "github-api"):
            self.assertIn(expected, mirrors)

    def test_rows_have_collector_source_and_mirrors(self) -> None:
        table = adversary_mirror_table()
        self.assertTrue(table)
        for row in table:
            self.assertEqual(set(row), {"collector", "source", "mirrors"})


if __name__ == "__main__":
    unittest.main()
