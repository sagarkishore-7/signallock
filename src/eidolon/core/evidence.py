"""Typed evidence emitted by collectors.

Collectors never return a flattened profile or raw scraped text. They emit
:class:`Observation` records — one typed, provenance-stamped, confidence-scored
fact each. This preserves where every datum came from and which attacker tool
would have produced it, which the resolver and exposure model both depend on.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .enums import AttributeKind, SourceClass, Visibility


@dataclass(frozen=True)
class Observation:
    """One typed fact harvested about a subject from one source.

    Attributes:
        subject_id: The consented subject this fact concerns.
        source: Which attacker source class produced it.
        attr_kind: The typed kind of attribute.
        value: The trimmed value (free text, a year as string, or a platform
            name for presence signals). Case is preserved here; lowercasing for
            matching happens when the resolver builds token buckets.
        confidence: Collector confidence in [0, 1].
        collected_at: ISO timestamp of collection.
        provenance: Human-readable origin (URL, API endpoint, snapshot id).
        mirrors: The attacker tool/technique this collection mirrors
            (e.g. "maigret", "holehe", "hibp"), for the adversary-mirror report.
        visibility: How accessible the datum is (PUBLIC / GATED / PRIVATE).
            Defaults to PUBLIC so existing data and snapshots are unaffected.
    """

    subject_id: str
    source: SourceClass
    attr_kind: AttributeKind
    value: str
    confidence: float
    collected_at: str
    provenance: str
    mirrors: str
    visibility: Visibility = Visibility.PUBLIC

    def __post_init__(self) -> None:
        if not self.subject_id.strip():
            raise ValueError("Observation.subject_id must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Observation.confidence must be in [0, 1]")
        # Trim only; the resolver lowercases when building token buckets.
        object.__setattr__(self, "value", self.value.strip())
        if not self.value:
            raise ValueError("Observation.value must be non-empty")

    @property
    def is_presence_only(self) -> bool:
        """True for account-exists signals that carry no exploitable payload."""
        return self.attr_kind is AttributeKind.PLATFORM_PRESENCE

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["source"] = self.source.value
        data["attr_kind"] = self.attr_kind.value
        data["visibility"] = self.visibility.value
        return data
