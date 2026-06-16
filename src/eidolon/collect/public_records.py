"""Public records: the defensive mirror of data-broker / voter-roll lookups.

An attacker buys or scrapes data-broker records for a target's address, date of
birth, phone, and relatives — high-value personal trivia for targeted guessing.
This is the most invasive source, so it is the most tightly gated: there is no
live path. Any attempt to run live raises :class:`CollectorError`. The only
supported route is an operator-authored, consented snapshot, from which it emits
ADDRESS / DATE_OF_BIRTH / RELATIVE / PHONE observations.
"""

from __future__ import annotations

from pathlib import Path

from ..core.enums import AttributeKind, SourceClass
from ..core.errors import CollectorError
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register
from .snapshot import load_snapshot

#: Attribute kinds this collector may surface from a consented snapshot.
_ALLOWED_KINDS = frozenset(
    {
        AttributeKind.ADDRESS,
        AttributeKind.DATE_OF_BIRTH,
        AttributeKind.RELATIVE,
        AttributeKind.PHONE,
    }
)


@register
class PublicRecords(Collector):
    """Emit public-records observations from a consented snapshot only.

    Construct with a ``snapshot_path``; only ADDRESS / DATE_OF_BIRTH / RELATIVE /
    PHONE observations survive the filter. Setting ``live=True`` selects the
    documented-but-disabled data-broker path, which raises
    :class:`CollectorError`: live broker lookups are not enabled by design.
    """

    source = SourceClass.PUBLIC_RECORDS
    mirrors = "data-broker"

    def __init__(
        self,
        *,
        snapshot_path: str | Path | None = None,
        live: bool = False,
    ) -> None:
        self._live = live
        self._snapshot = (
            load_snapshot(snapshot_path) if snapshot_path is not None else None
        )

    def _collect(self, identity: ConsentedIdentity) -> list[Observation]:
        if self._live:
            raise CollectorError(
                "live data-broker path not enabled; use a consented snapshot"
            )
        if self._snapshot is None:
            return []
        return [
            obs
            for obs in self._snapshot
            if obs.subject_id == identity.subject_id
            and obs.attr_kind in _ALLOWED_KINDS
        ]
