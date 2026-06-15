"""Username enumeration: the defensive mirror of maigret / Sherlock.

An attacker runs the same username across hundreds of sites to map a target's
account footprint. The defensive mirror only ever checks an explicit
*owned-allowlist* of platform URL templates (sites the operator controls or has
consent to probe) and emits PLATFORM_PRESENCE signals — account-exists facts
that carry no exploitable payload. Off the allowlist, and with no snapshot, the
collector returns nothing: it never fans out across the open web.
"""

from __future__ import annotations

from pathlib import Path

from ..core.enums import AttributeKind, SourceClass
from ..core.errors import CollectorError
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register
from .snapshot import load_snapshot


@register
class UsernameEnumerator(Collector):
    """Check a username against an owned-allowlist of platforms only.

    ``allowlist`` maps a platform label to a URL template containing
    ``{username}``. With an injected client, an allowlisted URL that returns 200
    yields one PLATFORM_PRESENCE observation. Offline default: a consented
    snapshot, or ``[]``.
    """

    source = SourceClass.USERNAME_ENUM
    mirrors = "maigret"

    def __init__(
        self,
        *,
        client=None,
        allowlist: dict[str, str] | None = None,
        snapshot_path: str | Path | None = None,
    ) -> None:
        self._client = client
        self._allowlist = dict(allowlist or {})
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
        username = identity.seeds.username
        if not username or self._client is None or not self._allowlist:
            return []

        observations: list[Observation] = []
        for platform, template in self._allowlist.items():
            url = template.format(username=username)
            try:
                response = self._client.get(url)
                status = getattr(response, "status_code", None)
            except Exception as exc:  # noqa: BLE001 - normalise transport errors
                raise CollectorError(
                    f"Username check failed for {platform}: {exc}"
                ) from exc
            if status == 200:
                observations.append(
                    self._obs(
                        identity.subject_id,
                        AttributeKind.PLATFORM_PRESENCE,
                        platform,
                        confidence=0.9,
                        provenance=f"username-enum:{platform}",
                    )
                )
        return observations
