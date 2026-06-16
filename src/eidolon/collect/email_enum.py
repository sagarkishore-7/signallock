"""Email enumeration: the defensive mirror of holehe / h8mail.

An attacker submits a target's email to many sites' password-reset / signup
endpoints to learn where they hold accounts. The defensive mirror restricts this
to an explicit *owned-allowlist* of endpoints and emits only PLATFORM_PRESENCE
signals (account-exists, no payload). Off the allowlist, and with no snapshot,
it returns nothing.
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
class EmailEnumerator(Collector):
    """Check an email against an owned-allowlist of endpoints only.

    ``allowlist`` maps a platform label to a URL template containing ``{email}``.
    With an injected client, an allowlisted URL returning 200 yields one
    PLATFORM_PRESENCE observation. Offline default: a consented snapshot or ``[]``.
    """

    source = SourceClass.EMAIL_ENUM
    mirrors = "holehe"

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
        email = identity.seeds.email
        if not email or self._client is None or not self._allowlist:
            return []

        observations: list[Observation] = []
        for platform, template in self._allowlist.items():
            url = template.format(email=email)
            try:
                response = self._client.get(url)
                status = getattr(response, "status_code", None)
            except Exception as exc:  # noqa: BLE001 - normalise transport errors
                raise CollectorError(
                    f"Email check failed for {platform}: {exc}"
                ) from exc
            if status == 200:
                observations.append(
                    self._obs(
                        identity.subject_id,
                        AttributeKind.PLATFORM_PRESENCE,
                        platform,
                        confidence=0.9,
                        provenance=f"email-enum:{platform}",
                    )
                )
        return observations
