"""Footprint search: the defensive mirror of theHarvester / SpiderFoot.

An attacker sweeps a target's domain for emails, usernames, subdomains and
related accounts. The defensive mirror restricts that sweep to *owned domains*
(domains the operator controls or has consent to enumerate) and emits typed
observations. Off an owned domain, and with no snapshot, it returns nothing: it
never fans out across the open web.
"""

from __future__ import annotations

from pathlib import Path

from ..core.enums import SourceClass
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register
from .snapshot import load_snapshot


@register
class FootprintSearch(Collector):
    """Enumerate a footprint over owned domains only, or replay a snapshot.

    ``owned_domains`` is the allowlist of domains this collector may touch. The
    live path stays disabled in the offline-first default; the consented path is
    an operator-authored snapshot. Offline default: a snapshot or ``[]``.
    """

    source = SourceClass.FOOTPRINT_SEARCH
    mirrors = "theharvester"

    def __init__(
        self,
        *,
        client=None,
        owned_domains: list[str] | None = None,
        snapshot_path: str | Path | None = None,
    ) -> None:
        self._client = client
        self._owned_domains = frozenset(
            d.strip().lower() for d in (owned_domains or []) if d.strip()
        )
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
        domain = identity.seeds.domain
        if not domain or domain.strip().lower() not in self._owned_domains:
            # Off an owned domain, the footprint sweep never runs.
            return []
        # Live enumeration over an owned domain is intentionally not auto-run in
        # the offline-first build; operators supply a consented snapshot instead.
        return []
