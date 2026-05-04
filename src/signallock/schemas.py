"""Core schemas for the SignalLock prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class RoleSeniority(str, Enum):
    """Normalized role seniority values."""

    INDIVIDUAL_CONTRIBUTOR = "INDIVIDUAL_CONTRIBUTOR"
    MANAGER = "MANAGER"
    DIRECTOR = "DIRECTOR"
    VP = "VP"
    C_SUITE = "C_SUITE"


class Platform(str, Enum):
    """Supported public platform types."""

    LINKEDIN = "LINKEDIN"
    GITHUB = "GITHUB"
    X = "X"
    PERSONAL_WEBSITE = "PERSONAL_WEBSITE"
    SPEAKER_BIO = "SPEAKER_BIO"
    UNIVERSITY_PROFILE = "UNIVERSITY_PROFILE"
    COMPANY_DIRECTORY = "COMPANY_DIRECTORY"


class RiskBand(str, Enum):
    """Bounded risk labels used across the prototype."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def _normalize_list(values: list[str]) -> list[str]:
    """Lower noise in list fields while preserving order."""
    seen: set[str] = set()
    normalized: list[str] = []

    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)

    return normalized


def _normalize_tokens(values: list[str]) -> list[str]:
    """Normalize token lists to unique lowercase values."""
    seen: set[str] = set()
    normalized: list[str] = []

    for value in values:
        cleaned = value.strip().lower()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


@dataclass
class PublicProfile:
    """Organization-approved or synthetic public identity record."""

    employee_id: str
    full_name: str
    title: str
    department: str
    organization: str
    role_seniority: RoleSeniority
    email_format: str
    location: str
    tenure_start_year: int
    platforms: list[Platform] = field(default_factory=list)
    public_usernames: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    preferred_name: str | None = None
    education: str | None = None
    bio: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize values."""
        self.employee_id = self.employee_id.strip()
        self.full_name = self.full_name.strip()
        self.title = self.title.strip()
        self.department = self.department.strip()
        self.organization = self.organization.strip()
        self.email_format = self.email_format.strip()
        self.location = self.location.strip()
        self.preferred_name = self.preferred_name.strip() if self.preferred_name else None
        self.education = self.education.strip() if self.education else None
        self.bio = self.bio.strip() if self.bio else None
        self.public_usernames = _normalize_list(self.public_usernames)
        self.interests = _normalize_list(self.interests)

        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if not self.full_name:
            raise ValueError("full_name must be non-empty")
        if not self.title:
            raise ValueError("title must be non-empty")
        if not self.department:
            raise ValueError("department must be non-empty")
        if not self.organization:
            raise ValueError("organization must be non-empty")
        if not self.email_format:
            raise ValueError("email_format must be non-empty")
        if not self.location:
            raise ValueError("location must be non-empty")
        if not 1970 <= self.tenure_start_year <= 2100:
            raise ValueError("tenure_start_year must be between 1970 and 2100")

    @property
    def platform_count(self) -> int:
        """Return the number of public platforms."""
        return len(self.platforms)

    def to_dict(self) -> dict[str, object]:
        """Convert the profile to a JSON-serializable dictionary."""
        data = asdict(self)
        data["role_seniority"] = self.role_seniority.value
        data["platforms"] = [platform.value for platform in self.platforms]
        return data


@dataclass
class AttributeVector:
    """Normalized public attribute buckets for later feature extraction."""

    employee_id: str
    role_seniority: RoleSeniority
    name_tokens: list[str]
    organization_tokens: list[str]
    temporal_tokens: list[str]
    identity_tokens: list[str]
    context_tokens: list[str]
    platform_count: int

    def __post_init__(self) -> None:
        """Normalize token sets."""
        self.name_tokens = _normalize_tokens(self.name_tokens)
        self.organization_tokens = _normalize_tokens(self.organization_tokens)
        self.temporal_tokens = _normalize_tokens(self.temporal_tokens)
        self.identity_tokens = _normalize_tokens(self.identity_tokens)
        self.context_tokens = _normalize_tokens(self.context_tokens)

        if not self.employee_id.strip():
            raise ValueError("employee_id must be non-empty")
        if self.platform_count < 0:
            raise ValueError("platform_count must be non-negative")

    def to_dict(self) -> dict[str, object]:
        """Convert the vector to a JSON-serializable dictionary."""
        data = asdict(self)
        data["role_seniority"] = self.role_seniority.value
        return data


@dataclass
class ExposureAssessment:
    """Interpretable baseline exposure score output."""

    employee_id: str
    score: float
    band: RiskBand
    component_scores: dict[str, float]
    top_factors: list[str]

    def __post_init__(self) -> None:
        """Validate core assessment shape."""
        self.employee_id = self.employee_id.strip()
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        """Convert the assessment to a JSON-serializable dictionary."""
        data = asdict(self)
        data["band"] = self.band.value
        return data
