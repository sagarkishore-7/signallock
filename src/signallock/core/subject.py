"""The resolved subject: a normalized dossier assembled from observations.

A :class:`Subject` is what the resolver produces by merging all observations for
one identity. It carries typed token buckets (the guessing material), the set of
platforms the subject was resolved on, and per-source coverage — the inputs both
the exposure model and the predictability simulator consume.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .enums import RoleSeniority, SourceClass, TokenBucket


def _dedupe_lower(values: list[str]) -> list[str]:
    """Unique, order-preserving, lowercased, non-empty tokens."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = value.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


@dataclass
class Subject:
    """A resolved, normalized dossier for one consented subject.

    Attributes:
        subject_id: The consented subject id.
        role_seniority: Resolved seniority (defaults to IC when unknown).
        token_buckets: Typed guessing material keyed by :class:`TokenBucket`.
        platforms: Platforms (source classes) the subject was resolved on.
        source_coverage: Count of distinct attribute kinds harvested per source,
            used by the exposure model's depth term.
        breach_count: Number of distinct breaches the subject appeared in.
    """

    subject_id: str
    role_seniority: RoleSeniority = RoleSeniority.INDIVIDUAL_CONTRIBUTOR
    token_buckets: dict[TokenBucket, list[str]] = field(default_factory=dict)
    platforms: list[SourceClass] = field(default_factory=list)
    source_coverage: dict[SourceClass, int] = field(default_factory=dict)
    breach_count: int = 0

    def __post_init__(self) -> None:
        self.subject_id = self.subject_id.strip()
        if not self.subject_id:
            raise ValueError("Subject.subject_id must be non-empty")
        # Ensure every bucket exists and is normalized.
        normalized: dict[TokenBucket, list[str]] = {}
        for bucket in TokenBucket:
            normalized[bucket] = _dedupe_lower(self.token_buckets.get(bucket, []))
        self.token_buckets = normalized

    def tokens(self, bucket: TokenBucket) -> list[str]:
        """Return tokens for one bucket (possibly empty)."""
        return self.token_buckets.get(bucket, [])

    def all_tokens(self) -> list[str]:
        """All guessing tokens across buckets, de-duplicated."""
        flat: list[str] = []
        for bucket in TokenBucket:
            flat.extend(self.token_buckets.get(bucket, []))
        return _dedupe_lower(flat)

    @property
    def platform_count(self) -> int:
        return len(self.platforms)

    @property
    def personal_trivia(self) -> list[str]:
        """The high-value personal-trivia tokens (pets, family, affiliations)."""
        return self.token_buckets.get(TokenBucket.PERSONAL_TRIVIA, [])

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["role_seniority"] = self.role_seniority.value
        data["token_buckets"] = {
            bucket.value: tokens for bucket, tokens in self.token_buckets.items()
        }
        data["platforms"] = [p.value for p in self.platforms]
        data["source_coverage"] = {
            source.value: count for source, count in self.source_coverage.items()
        }
        return data
