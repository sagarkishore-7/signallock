"""Consent spine: identities, consent records, and the hard consent gate.

Every collector and the guess simulator call :func:`require_consent` before
touching a network source or a password. An identity that is not backed by a
consent record in the active roster is refused with :class:`ConsentError`. This
is the single ethical boundary the rest of the system is built on top of.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .errors import ConsentError


@dataclass(frozen=True)
class IdentitySeeds:
    """The seeds an attacker would pivot from: email, username, name, domain.

    All optional, but at least one must be present. These are the entry points
    every collector resolves the subject from.
    """

    email: str | None = None
    username: str | None = None
    name: str | None = None
    domain: str | None = None

    def __post_init__(self) -> None:
        if not any((self.email, self.username, self.name, self.domain)):
            raise ValueError("IdentitySeeds requires at least one seed value")

    def to_dict(self) -> dict[str, object]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class ConsentRecord:
    """Signed authorization to collect on, and assess, one subject.

    ``is_dummy`` flags operator-created dummy accounts used purely as OSINT
    *sources* for the research (see ``docs/OSINT_COLLECTION_PROTOCOL.md``).
    ``allowed_sources`` optionally restricts which collectors may run; an empty
    set means all sources are permitted.
    """

    subject_id: str
    consent_ref: str           # path/id of the signed consent artifact
    granted_at: str            # ISO date
    is_dummy: bool = False
    allowed_sources: frozenset[str] = field(default_factory=frozenset)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["allowed_sources"] = sorted(self.allowed_sources)
        return data


@dataclass(frozen=True)
class ConsentedIdentity:
    """A subject we are authorized to collect on, bound to its consent record."""

    subject_id: str
    seeds: IdentitySeeds
    consent: ConsentRecord

    def __post_init__(self) -> None:
        if self.subject_id != self.consent.subject_id:
            raise ValueError(
                "ConsentedIdentity.subject_id must match its consent record"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_id": self.subject_id,
            "seeds": self.seeds.to_dict(),
            "consent": self.consent.to_dict(),
        }


class ConsentRoster:
    """The set of subjects the operator is authorized to assess."""

    def __init__(self, records: dict[str, ConsentRecord] | None = None) -> None:
        self._records: dict[str, ConsentRecord] = dict(records or {})

    def __contains__(self, subject_id: object) -> bool:
        return subject_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def subject_ids(self) -> list[str]:
        return sorted(self._records)

    def get(self, subject_id: str) -> ConsentRecord | None:
        return self._records.get(subject_id)

    def add(self, record: ConsentRecord) -> None:
        self._records[record.subject_id] = record

    @classmethod
    def from_dicts(cls, raw: list[dict[str, object]]) -> "ConsentRoster":
        roster = cls()
        for item in raw:
            roster.add(
                ConsentRecord(
                    subject_id=str(item["subject_id"]),
                    consent_ref=str(item["consent_ref"]),
                    granted_at=str(item["granted_at"]),
                    is_dummy=bool(item.get("is_dummy", False)),
                    allowed_sources=frozenset(
                        str(s) for s in item.get("allowed_sources", [])
                    ),
                )
            )
        return roster

    @classmethod
    def load(cls, path: str | Path) -> "ConsentRoster":
        """Load a roster JSON: ``{"subjects": [{...consent records...}]}``."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        records = payload.get("subjects", payload) if isinstance(payload, dict) else payload
        return cls.from_dicts(records)


def require_consent(
    identity: ConsentedIdentity,
    roster: ConsentRoster,
    *,
    source: str | None = None,
) -> ConsentRecord:
    """Hard gate: confirm ``identity`` is consented before any collection/scoring.

    Args:
        identity: The subject being acted on.
        roster: The active consent roster.
        source: Optional collector/source name; checked against the record's
            ``allowed_sources`` allowlist when that allowlist is non-empty.

    Returns:
        The matching :class:`ConsentRecord`.

    Raises:
        ConsentError: If the subject is not in the roster or the source is not
            permitted for that subject.
    """
    record = roster.get(identity.subject_id)
    if record is None:
        raise ConsentError(
            f"No consent on record for subject '{identity.subject_id}'. "
            "Collection and scoring are refused for non-consented identities."
        )
    if source and record.allowed_sources and source not in record.allowed_sources:
        raise ConsentError(
            f"Source '{source}' is not permitted for subject "
            f"'{identity.subject_id}' under its consent record."
        )
    return record
