"""Professional profile: the defensive mirror of a LinkedIn / directory snapshot.

An attacker pulls a target's employer, role/title, tenure, and education from
LinkedIn or a company directory — strong organisation and temporal seeds. These
sources are ToS-hostile to automated scraping, so the only supported path here
is a *manual, operator-authored consented snapshot*. The live path is documented
as deliberately not auto-scraped; there is no automated network collection.
"""

from __future__ import annotations

from pathlib import Path

from ..core.enums import SourceClass
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register
from .snapshot import load_snapshot


@register
class ProfessionalProfile(Collector):
    """Replay an operator-authored professional snapshot.

    Construct with a ``snapshot_path`` to a consented snapshot (employer, title,
    tenure, education). There is no live path: LinkedIn / directory data is never
    auto-scraped, only ingested as a manual snapshot. Offline default: a snapshot
    or ``[]``.
    """

    source = SourceClass.PROFESSIONAL
    mirrors = "linkedin-snapshot"

    def __init__(
        self,
        *,
        snapshot_path: str | Path | None = None,
    ) -> None:
        self._snapshot = (
            load_snapshot(snapshot_path) if snapshot_path is not None else None
        )

    def _collect(self, identity: ConsentedIdentity) -> list[Observation]:
        if self._snapshot is None:
            return []
        return [
            obs
            for obs in self._snapshot
            if obs.subject_id == identity.subject_id
        ]
