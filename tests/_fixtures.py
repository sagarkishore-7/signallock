"""Shared offline fixtures for SignalLock v2 tests (clearly fake data)."""

from __future__ import annotations

from signallock.core import (
    AttributeKind,
    ConsentedIdentity,
    ConsentRecord,
    ConsentRoster,
    IdentitySeeds,
    Observation,
    SourceClass,
)

SUBJECT_ID = "dummy-ghost"


def make_identity(subject_id: str = SUBJECT_ID) -> ConsentedIdentity:
    return ConsentedIdentity(
        subject_id=subject_id,
        seeds=IdentitySeeds(username="ghostrider", email="ghost@example.com"),
        consent=ConsentRecord(
            subject_id=subject_id,
            consent_ref="configs/consent_records/dummy-ghost.json",
            granted_at="2026-06-01",
            is_dummy=True,
        ),
    )


def make_roster(*identities: ConsentedIdentity) -> ConsentRoster:
    identities = identities or (make_identity(),)
    return ConsentRoster({i.subject_id: i.consent for i in identities})


def make_observations(subject_id: str = SUBJECT_ID) -> list[Observation]:
    """A dummy subject exposed across social, code, and professional sources.

    Personal trivia (pet 'rex') + a significant year (2014) make 'rex2014' a
    reachable targeted guess — the canonical weak-password demonstration.
    """
    t = "2026-06-01T00:00:00Z"

    def obs(source: SourceClass, kind: AttributeKind, value: str, mirrors: str,
            conf: float = 0.9) -> Observation:
        return Observation(subject_id, source, kind, value, conf, t,
                           f"fixture:{source.value}", mirrors)

    return [
        obs(SourceClass.SOCIAL, AttributeKind.NAME, "Alice Smith", "snapshot"),
        obs(SourceClass.SOCIAL, AttributeKind.PET_NAME, "Rex", "cupp"),
        obs(SourceClass.SOCIAL, AttributeKind.AFFILIATION, "Red Sox", "cupp"),
        obs(SourceClass.SOCIAL, AttributeKind.SIGNIFICANT_YEAR, "2014", "cupp"),
        obs(SourceClass.SOCIAL, AttributeKind.INTEREST, "hiking", "cupp"),
        obs(SourceClass.CODE, AttributeKind.USERNAME, "ghostrider", "maigret"),
        obs(SourceClass.CODE, AttributeKind.LANGUAGE, "python", "github-api"),
        obs(SourceClass.PROFESSIONAL, AttributeKind.ORGANIZATION, "Acme Corp",
            "snapshot"),
        obs(SourceClass.PROFESSIONAL, AttributeKind.ROLE_TITLE, "Director",
            "snapshot"),
        obs(SourceClass.USERNAME_ENUM, AttributeKind.PLATFORM_PRESENCE, "github",
            "maigret"),
    ]
