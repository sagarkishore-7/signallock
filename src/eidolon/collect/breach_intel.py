"""Breach intelligence: the defensive mirror of HIBP / COMB — structure only.

An attacker correlates a target's email against breach corpora to learn which
breaches they appear in and, far more dangerously, the *structural habits* of
their reused passwords ("word+4digits", "Capital+year"). This collector mirrors
that reconnaissance but is deliberately neutered: it never stores or emits
cleartext third-party credentials. From a consented snapshot it emits only
:data:`AttributeKind.BREACH` (the breach name) and
:data:`AttributeKind.STRUCTURE_PRIOR` (an abstract structural pattern string).

The live HIBP path is a documented stub: pulling third-party breach data into
the system is gated off and raises :class:`CollectorError`. The consented
snapshot — where an operator records only the structural prior, never a
password — is the sole supported path.
"""

from __future__ import annotations

from pathlib import Path

from ..core.enums import AttributeKind, SourceClass
from ..core.errors import CollectorError
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register
from .snapshot import load_snapshot

#: Attribute kinds this collector is permitted to surface. BREACH names and
#: abstract STRUCTURE_PRIOR patterns only — never a cleartext credential.
_ALLOWED_KINDS = frozenset({AttributeKind.BREACH, AttributeKind.STRUCTURE_PRIOR})


@register
class BreachIntel(Collector):
    """Emit breach names and structural password priors from a snapshot.

    Construct with a ``snapshot_path`` to an operator-authored consented
    snapshot. Only BREACH and STRUCTURE_PRIOR observations survive the filter;
    any other attribute kind in the snapshot is dropped so no cleartext
    credential can leak through this source.

    Setting ``live=True`` selects the documented-but-disabled HIBP path, which
    raises :class:`CollectorError`: live third-party breach lookups are not
    enabled by design.
    """

    source = SourceClass.BREACH_INTEL
    mirrors = "hibp"

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
                "live HIBP path not enabled; use a consented snapshot"
            )
        if self._snapshot is None:
            return []
        return [
            obs
            for obs in self._snapshot
            if obs.subject_id == identity.subject_id
            and obs.attr_kind in _ALLOWED_KINDS
        ]
