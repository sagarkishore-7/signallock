"""Operator-authored consented snapshots: how ToS-hostile sources enter.

Some of the richest attacker material (LinkedIn, public records, and ToS-hostile
social platforms) cannot be auto-scraped lawfully. The defensive system instead
ingests *operator-authored, consented snapshots*: a human collects the subject's
own public footprint under signed consent and serialises it as typed
observations. This module loads that JSON and exposes a :class:`Collector` that
replays it through the same consent gate as the live collectors.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..core.enums import AttributeKind, SourceClass
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register

_DEFAULT_CONFIDENCE = 0.9


def load_snapshot(path: str | Path) -> list[Observation]:
    """Load a consented snapshot JSON into typed observations.

    Expected shape::

        {
          "subject_id": "...",
          "observations": [
            {"source": "SOCIAL", "attr_kind": "PET_NAME", "value": "Rex",
             "confidence": 0.9, "mirrors": "cupp", "provenance": "snapshot:ig"}
          ]
        }

    ``collected_at`` and ``provenance`` are optional and default to sensible
    values. ``source`` and ``attr_kind`` are the string names of the
    :class:`SourceClass` / :class:`AttributeKind` enum members.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    subject_id = str(payload["subject_id"])
    default_time = datetime.now(timezone.utc).isoformat()

    observations: list[Observation] = []
    for raw in payload.get("observations", []):
        observations.append(
            Observation(
                subject_id=subject_id,
                source=SourceClass(str(raw["source"])),
                attr_kind=AttributeKind(str(raw["attr_kind"])),
                value=str(raw["value"]),
                confidence=float(raw.get("confidence", _DEFAULT_CONFIDENCE)),
                collected_at=str(raw.get("collected_at", default_time)),
                provenance=str(raw.get("provenance", "snapshot")),
                mirrors=str(raw.get("mirrors", "snapshot")),
            )
        )
    return observations


@register
class SnapshotCollector(Collector):
    """Replay a loaded consented snapshot through the consent gate.

    Mirrors the operator's manual collection step: it carries no live path, just
    the observations an operator authored. Pass either a pre-loaded observation
    list or a ``snapshot_path`` to load on construction.
    """

    source = SourceClass.SNAPSHOT
    mirrors = "operator-snapshot"

    def __init__(
        self,
        observations: list[Observation] | None = None,
        *,
        snapshot_path: str | Path | None = None,
    ) -> None:
        loaded: list[Observation] = list(observations or [])
        if snapshot_path is not None:
            loaded.extend(load_snapshot(snapshot_path))
        self._observations = loaded

    def _collect(self, identity: ConsentedIdentity) -> list[Observation]:
        return [
            obs
            for obs in self._observations
            if obs.subject_id == identity.subject_id
        ]
