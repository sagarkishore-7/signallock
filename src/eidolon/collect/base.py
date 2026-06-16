"""Collector base class, the consent gate, and the adversary-mirror registry.

Every collector in this package is the defensive mirror of one attacker OSINT
tool (maigret, holehe, hibp, theHarvester, ...). A collector resolves a subject
from its consented seeds and emits typed :class:`Observation` records — never a
flattened profile or raw scraped text.

The single ethical invariant lives here: :meth:`Collector.collect` calls
:func:`require_consent` *first*, before any subclass ``_collect`` touches a
network source. A collector cannot be run against a non-consented identity.

The :data:`MIRROR_REGISTRY` and :func:`register` decorator let every collector
self-declare the attacker tool it reproduces; :func:`adversary_mirror_table`
renders that registry into the rows that generate ``docs/ADVERSARY_MIRROR.md``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from ..core.enums import AttributeKind, SourceClass
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity, ConsentRoster, require_consent


class Collector(ABC):
    """Abstract base for every adversary-mirrored OSINT collector.

    Subclasses set two class attributes — :attr:`source` (the
    :class:`SourceClass` they belong to) and :attr:`mirrors` (the attacker tool
    they reproduce, e.g. ``"maigret"``) — and implement :meth:`_collect`.

    Public callers use :meth:`collect`, which enforces the consent gate before
    delegating. Subclasses must not call network code in ``__init__`` or in the
    :meth:`_obs` / rate-limit helpers; collection happens only inside
    :meth:`_collect`, behind the gate.
    """

    #: The attacker source class this collector belongs to.
    source: SourceClass
    #: The attacker tool/technique this collector mirrors (for the report).
    mirrors: str = ""

    def collect(
        self,
        identity: ConsentedIdentity,
        *,
        roster: ConsentRoster,
    ) -> list[Observation]:
        """Enforce consent, then collect typed observations for ``identity``.

        Raises:
            ConsentError: If ``identity`` is not consented for this source.
            CollectorError: If the underlying collection fails irrecoverably.
        """
        require_consent(identity, roster, source=self.source.value)
        self._rate_limit()
        return self._collect(identity)

    @abstractmethod
    def _collect(self, identity: ConsentedIdentity) -> list[Observation]:
        """Collect observations for an already-consented identity."""
        raise NotImplementedError

    def _obs(
        self,
        subject_id: str,
        attr_kind: AttributeKind,
        value: str,
        *,
        confidence: float = 0.9,
        provenance: str,
    ) -> Observation:
        """Stamp a typed observation with this collector's source/mirrors/time."""
        return Observation(
            subject_id=subject_id,
            source=self.source,
            attr_kind=attr_kind,
            value=value,
            confidence=confidence,
            collected_at=datetime.now(timezone.utc).isoformat(),
            provenance=provenance,
            mirrors=self.mirrors,
        )

    def _rate_limit(self) -> None:
        """No-op rate-limit/cache hook.

        A real deployment would back this with a token bucket and an on-disk
        response cache. The offline-first design keeps it a stub so helpers and
        tests never sleep or hit the network.
        """

    def _cache_key(self, identity: ConsentedIdentity) -> str:
        """Stable cache key for ``identity`` under this source (no network)."""
        return f"{self.source.value}:{identity.subject_id}"


#: Every registered collector class, in registration order.
MIRROR_REGISTRY: list[type[Collector]] = []


def register(cls: type[Collector]) -> type[Collector]:
    """Class decorator: append ``cls`` to :data:`MIRROR_REGISTRY`."""
    if cls not in MIRROR_REGISTRY:
        MIRROR_REGISTRY.append(cls)
    return cls


def adversary_mirror_table() -> list[dict]:
    """Render the registry into ``{collector, source, mirrors}`` rows.

    Used to generate ``docs/ADVERSARY_MIRROR.md`` so the mapping from each
    collector to the attacker tool it reproduces stays in sync with the code.
    """
    return [
        {
            "collector": cls.__name__,
            "source": cls.source.value,
            "mirrors": cls.mirrors,
        }
        for cls in MIRROR_REGISTRY
    ]
