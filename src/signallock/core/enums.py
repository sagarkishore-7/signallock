"""Core enumerations for SignalLock v2.

These enums are the shared vocabulary across the adversary-mirrored pipeline:
collection sources, attribute kinds, typed token buckets, risk bands, hardening
actions, and the bounded guess budgets defined in ``docs/THREAT_MODEL.md``.

The ``RiskBand``, ``HardeningAction`` and ``RoleSeniority`` enums are preserved
verbatim from the v1 prototype so existing policy semantics and the dashboard
carry over unchanged.
"""

from __future__ import annotations

from enum import Enum, IntEnum


class RiskBand(str, Enum):
    """Bounded risk labels used across the pipeline."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        """Ordinal severity (LOW=0 .. CRITICAL=3) for comparisons."""
        return _RISK_BAND_ORDER[self]

    # Explicit ordering by severity rank; overrides str's lexical comparisons
    # so min()/max()/sorted() behave by risk severity.
    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RiskBand):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: object) -> bool:
        if not isinstance(other, RiskBand):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, RiskBand):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, RiskBand):
            return NotImplemented
        return self.rank >= other.rank


_RISK_BAND_ORDER: dict[RiskBand, int] = {
    RiskBand.LOW: 0,
    RiskBand.MEDIUM: 1,
    RiskBand.HIGH: 2,
    RiskBand.CRITICAL: 3,
}


class HardeningAction(str, Enum):
    """Supported hardening actions for the policy engine."""

    ALLOW = "ALLOW"
    WARN = "WARN"
    REQUIRE_STRONGER_PASSWORD = "REQUIRE_STRONGER_PASSWORD"
    ENFORCE_MFA = "ENFORCE_MFA"
    STEP_UP_AUTHENTICATION = "STEP_UP_AUTHENTICATION"
    PRIORITIZE_AWARENESS_TRAINING = "PRIORITIZE_AWARENESS_TRAINING"


class RoleSeniority(str, Enum):
    """Normalized role seniority values."""

    INDIVIDUAL_CONTRIBUTOR = "INDIVIDUAL_CONTRIBUTOR"
    MANAGER = "MANAGER"
    DIRECTOR = "DIRECTOR"
    VP = "VP"
    C_SUITE = "C_SUITE"

    @property
    def rank(self) -> int:
        """Ordinal seniority (IC=0 .. C_SUITE=4)."""
        return _SENIORITY_ORDER[self]


_SENIORITY_ORDER: dict[RoleSeniority, int] = {
    RoleSeniority.INDIVIDUAL_CONTRIBUTOR: 0,
    RoleSeniority.MANAGER: 1,
    RoleSeniority.DIRECTOR: 2,
    RoleSeniority.VP: 3,
    RoleSeniority.C_SUITE: 4,
}


class SourceClass(str, Enum):
    """Attacker OSINT source classes, each mirrored by one collector.

    See ``docs/ADVERSARY_MIRROR.md`` (generated from the collector registry) for
    the attacker tool each class reproduces.
    """

    USERNAME_ENUM = "USERNAME_ENUM"        # Maigret / Sherlock
    EMAIL_ENUM = "EMAIL_ENUM"              # Holehe / h8mail
    BREACH_INTEL = "BREACH_INTEL"          # HIBP / COMB (structure priors only)
    FOOTPRINT_SEARCH = "FOOTPRINT_SEARCH"  # theHarvester / SpiderFoot
    PROFESSIONAL = "PROFESSIONAL"          # LinkedIn / company directory
    CODE = "CODE"                          # GitHub / GitLab
    SOCIAL = "SOCIAL"                      # X / Instagram / Reddit / Mastodon
    WEB = "WEB"                            # personal sites / blogs
    PUBLIC_RECORDS = "PUBLIC_RECORDS"      # data brokers / voter rolls
    SNAPSHOT = "SNAPSHOT"                  # operator-authored consented snapshot


class AttributeKind(str, Enum):
    """Typed kinds of harvested attributes carried by an ``Observation``."""

    NAME = "NAME"
    PREFERRED_NAME = "PREFERRED_NAME"
    ORGANIZATION = "ORGANIZATION"
    ROLE_TITLE = "ROLE_TITLE"
    TENURE_YEAR = "TENURE_YEAR"
    EDUCATION = "EDUCATION"
    LOCATION = "LOCATION"
    USERNAME = "USERNAME"
    EMAIL = "EMAIL"
    LANGUAGE = "LANGUAGE"
    INTEREST = "INTEREST"
    PET_NAME = "PET_NAME"
    FAMILY_NAME = "FAMILY_NAME"
    AFFILIATION = "AFFILIATION"          # sports team, club, fandom
    SIGNIFICANT_YEAR = "SIGNIFICANT_YEAR"  # birth year, anniversary
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    RELATIVE = "RELATIVE"
    BREACH = "BREACH"                    # name of a breach the subject appeared in
    STRUCTURE_PRIOR = "STRUCTURE_PRIOR"  # structural password habit from prior breach
    PLATFORM_PRESENCE = "PLATFORM_PRESENCE"  # account-exists signal (no payload)


class TokenBucket(str, Enum):
    """Typed buckets the resolver sorts harvested tokens into.

    ``PERSONAL_TRIVIA`` and ``STRUCTURE_PRIOR`` are the high-value guessing
    material that distinguishes targeted attacks from generic dictionaries.
    """

    NAME = "name"
    ORGANIZATION = "organization"
    TEMPORAL = "temporal"
    IDENTITY = "identity"
    LOCATION = "location"
    INTEREST = "interest"
    PERSONAL_TRIVIA = "personal_trivia"
    STRUCTURE_PRIOR = "structure_prior"


#: Maps each harvested attribute kind to the token bucket it feeds.
ATTRIBUTE_TO_BUCKET: dict[AttributeKind, TokenBucket] = {
    AttributeKind.NAME: TokenBucket.NAME,
    AttributeKind.PREFERRED_NAME: TokenBucket.NAME,
    AttributeKind.FAMILY_NAME: TokenBucket.PERSONAL_TRIVIA,
    AttributeKind.RELATIVE: TokenBucket.PERSONAL_TRIVIA,
    AttributeKind.PET_NAME: TokenBucket.PERSONAL_TRIVIA,
    AttributeKind.AFFILIATION: TokenBucket.PERSONAL_TRIVIA,
    AttributeKind.INTEREST: TokenBucket.INTEREST,
    AttributeKind.ORGANIZATION: TokenBucket.ORGANIZATION,
    AttributeKind.ROLE_TITLE: TokenBucket.ORGANIZATION,
    AttributeKind.EDUCATION: TokenBucket.ORGANIZATION,
    AttributeKind.TENURE_YEAR: TokenBucket.TEMPORAL,
    AttributeKind.SIGNIFICANT_YEAR: TokenBucket.TEMPORAL,
    AttributeKind.DATE_OF_BIRTH: TokenBucket.TEMPORAL,
    AttributeKind.USERNAME: TokenBucket.IDENTITY,
    AttributeKind.EMAIL: TokenBucket.IDENTITY,
    AttributeKind.LANGUAGE: TokenBucket.IDENTITY,
    AttributeKind.LOCATION: TokenBucket.LOCATION,
    AttributeKind.ADDRESS: TokenBucket.LOCATION,
    AttributeKind.STRUCTURE_PRIOR: TokenBucket.STRUCTURE_PRIOR,
}


class Budget(IntEnum):
    """Bounded guessing budgets (number of attempts) per ``docs/THREAT_MODEL.md``.

    Each budget models a distinct attacker capability tier, from a handful of
    online guesses through an offline targeted-dictionary run.
    """

    B1 = 1
    B10 = 10
    B100 = 100
    B1000 = 1000
    B10000 = 10000

    @classmethod
    def ordered(cls) -> list["Budget"]:
        """Budgets from smallest to largest."""
        return sorted(cls, key=int)


#: Smallest budget at which a password falls -> risk band. A password reachable
#: within a few guesses is CRITICAL; one that survives the largest budget is LOW.
BUDGET_TO_BAND: dict[Budget | None, RiskBand] = {
    Budget.B1: RiskBand.CRITICAL,
    Budget.B10: RiskBand.CRITICAL,
    Budget.B100: RiskBand.HIGH,
    Budget.B1000: RiskBand.HIGH,
    Budget.B10000: RiskBand.MEDIUM,
    None: RiskBand.LOW,  # not reached within the largest budget
}
