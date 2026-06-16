"""Tests for accessibility-weighted (visibility) scoring."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eidolon.collect.snapshot import load_snapshot
from eidolon.core import AttributeKind, Observation, SourceClass, Visibility
from eidolon.exposure import assess_exposure
from eidolon.resolve import filter_by_visibility, resolve_subject


def _obs(kind: AttributeKind, value: str, vis: Visibility = Visibility.PUBLIC) -> Observation:
    return Observation("s", SourceClass.SOCIAL, kind, value, 0.9, "t", "p", "cupp", vis)


class VisibilityTests(unittest.TestCase):
    def test_observation_defaults_public(self) -> None:
        o = Observation(
            "s", SourceClass.SOCIAL, AttributeKind.PET_NAME, "rex", 0.9, "t", "p", "cupp"
        )
        self.assertEqual(o.visibility, Visibility.PUBLIC)
        self.assertEqual(o.to_dict()["visibility"], "PUBLIC")

    def test_filter_by_visibility_tiers(self) -> None:
        obs = [
            _obs(AttributeKind.NAME, "alice", Visibility.PUBLIC),
            _obs(AttributeKind.PET_NAME, "rex", Visibility.GATED),
            _obs(AttributeKind.DATE_OF_BIRTH, "1990", Visibility.PRIVATE),
        ]
        self.assertEqual(len(filter_by_visibility(obs, Visibility.PUBLIC)), 1)
        self.assertEqual(len(filter_by_visibility(obs, Visibility.GATED)), 2)
        self.assertEqual(len(filter_by_visibility(obs, Visibility.PRIVATE)), 3)

    def test_snapshot_reads_visibility_default_public(self) -> None:
        payload = {
            "subject_id": "s",
            "observations": [
                {"source": "SOCIAL", "attr_kind": "PET_NAME", "value": "rex",
                 "visibility": "GATED"},
                {"source": "CODE", "attr_kind": "NAME", "value": "alice"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            by_kind = {o.attr_kind: o.visibility for o in load_snapshot(path)}
        self.assertEqual(by_kind[AttributeKind.PET_NAME], Visibility.GATED)
        self.assertEqual(by_kind[AttributeKind.NAME], Visibility.PUBLIC)

    def test_public_only_lowers_exposure(self) -> None:
        obs = [
            _obs(AttributeKind.NAME, "alice smith", Visibility.PUBLIC),
            _obs(AttributeKind.PET_NAME, "rex", Visibility.GATED),
            _obs(AttributeKind.AFFILIATION, "red sox", Visibility.GATED),
            _obs(AttributeKind.SIGNIFICANT_YEAR, "1990", Visibility.GATED),
        ]
        full = assess_exposure(resolve_subject("s", obs))
        public = assess_exposure(
            resolve_subject("s", filter_by_visibility(obs, Visibility.PUBLIC))
        )
        self.assertLess(public.score, full.score)


if __name__ == "__main__":
    unittest.main()
