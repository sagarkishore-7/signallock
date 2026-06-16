"""Social collector: offline-first mirror of social-OSINT.

Mirrors the attacker step of mining a target's social platforms (X, Instagram,
Reddit, Mastodon) for pet names, affiliations, significant years, and interests.
Most of these platforms are ToS-hostile to scraping, so the consented path is an
operator-authored snapshot. A minimal live path exists only for open, public
APIs (Mastodon-style) and stays guarded behind an injectable client.
"""

from __future__ import annotations

from pathlib import Path

from ..core.enums import SourceClass
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register
from .snapshot import load_snapshot


@register
class SocialProfile(Collector):
    """Emit social observations, preferring a consented snapshot.

    If ``snapshot_path`` is given, its observations are returned (the consented
    path for ToS-hostile platforms). The live path is intentionally minimal and
    only reachable when a client is injected for an open public API.
    """

    source = SourceClass.SOCIAL
    mirrors = "social-osint"

    def __init__(
        self,
        *,
        client=None,
        snapshot_path: str | Path | None = None,
    ) -> None:
        self._client = client
        self._snapshot = (
            load_snapshot(snapshot_path) if snapshot_path is not None else None
        )

    def _collect(self, identity: ConsentedIdentity) -> list[Observation]:
        if self._snapshot is not None:
            return [
                obs
                for obs in self._snapshot
                if obs.subject_id == identity.subject_id
            ]
        # Offline-first: no snapshot and no live open-API integration enabled.
        return []
