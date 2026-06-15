"""Exposure model: quantify attack surface from a resolved Subject.

Departure from v1: exposure is a weighted blend of five attack-surface axes
multiplied by a **linkability multiplier** — how easily an attacker pivots one
seed across platforms to assemble a unified dossier. Linkability is the new
first-class dimension; the additive v1 heuristic could not express it.

    base_surface  S = Σ_axis weight_axis · axis_score      (0..100)
    linkability   L = 1 + α · (linkability_score / 100)    (1..1+α)
    exposure      E = min(100, S · L)

The five surface axes double as the ablation axes for the evaluation harness:
disabling one (``disabled_axes``) zeroes its contribution and renormalizes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..core.enums import RiskBand, SourceClass, TokenBucket
from ..core.subject import Subject

#: Surface-axis weights (sum to 1.0). Personal trivia is weighted highest
#: because it is the material targeted-guessing attacks exploit directly.
AXIS_WEIGHTS: dict[str, float] = {
    "discoverability": 0.15,
    "professional_visibility": 0.20,
    "personal_trivia_richness": 0.30,
    "breach_exposure": 0.20,
    "temporal_footprint": 0.15,
}

#: Linkability amplification factor: L ranges over [1, 1 + ALPHA].
ALPHA = 0.6

_DEPTH_CAP = 4
_DISCOVERY_SOURCES = (
    SourceClass.USERNAME_ENUM,
    SourceClass.EMAIL_ENUM,
    SourceClass.FOOTPRINT_SEARCH,
)


@dataclass
class ExposureAssessment:
    """Interpretable exposure score for one subject."""

    subject_id: str
    score: float
    band: RiskBand
    base_surface: float
    linkability_multiplier: float
    axis_scores: dict[str, float]      # the five surface axes
    linkability_score: float           # 0..100, drives the multiplier
    top_factors: list[str]

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("exposure score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["band"] = self.band.value
        return data


def _depth(subject: Subject, source: SourceClass) -> float:
    return min(1.0, subject.source_coverage.get(source, 0) / _DEPTH_CAP)


def band_from_score(score: float) -> RiskBand:
    """Map a 0..100 score onto a risk band (shared threshold convention)."""
    if score >= 75.0:
        return RiskBand.CRITICAL
    if score >= 50.0:
        return RiskBand.HIGH
    if score >= 25.0:
        return RiskBand.MEDIUM
    return RiskBand.LOW


def _discoverability(subject: Subject) -> float:
    breadth = min(1.0, subject.platform_count / 5.0)
    present = sum(1 for s in _DISCOVERY_SOURCES if s in subject.source_coverage)
    discovery = min(1.0, present / len(_DISCOVERY_SOURCES))
    return 100.0 * (0.5 * breadth + 0.5 * discovery)


def _professional_visibility(subject: Subject) -> float:
    return 100.0 * (
        0.4 * _depth(subject, SourceClass.PROFESSIONAL)
        + 0.3 * _depth(subject, SourceClass.CODE)
        + 0.3 * (subject.role_seniority.rank / 4.0)
    )


def _personal_trivia_richness(subject: Subject) -> float:
    trivia = len(subject.tokens(TokenBucket.PERSONAL_TRIVIA))
    interest = len(subject.tokens(TokenBucket.INTEREST))
    return 100.0 * min(1.0, (trivia + 0.5 * interest) / 8.0)


def _breach_exposure(subject: Subject) -> float:
    has_structure_prior = bool(subject.tokens(TokenBucket.STRUCTURE_PRIOR))
    return 100.0 * min(
        1.0, 0.3 * subject.breach_count + (0.4 if has_structure_prior else 0.0)
    )


def _temporal_footprint(subject: Subject) -> float:
    return 100.0 * min(1.0, len(subject.tokens(TokenBucket.TEMPORAL)) / 4.0)


def _linkability(subject: Subject) -> float:
    """0..100 cross-source linkability proxy.

    Combines breadth (how many platforms) with the strength of shared identity
    handles (username/email tokens that let an attacker pivot between them).
    """
    if subject.platform_count <= 1:
        return 0.0
    breadth = min(1.0, (subject.platform_count - 1) / 4.0)
    cross_ref = min(1.0, len(subject.tokens(TokenBucket.IDENTITY)) / 3.0)
    return 100.0 * (0.5 * breadth + 0.5 * cross_ref)


_AXIS_FUNCS = {
    "discoverability": _discoverability,
    "professional_visibility": _professional_visibility,
    "personal_trivia_richness": _personal_trivia_richness,
    "breach_exposure": _breach_exposure,
    "temporal_footprint": _temporal_footprint,
}

_AXIS_LABELS = {
    "discoverability": "Easily discoverable across public sources",
    "professional_visibility": "High professional visibility / seniority",
    "personal_trivia_richness": "Rich personal trivia exposed (pets, family, teams)",
    "breach_exposure": "Appears in known breaches with reuse patterns",
    "temporal_footprint": "Significant dates exposed (birth year, tenure)",
}


def assess_exposure(
    subject: Subject, *, disabled_axes: frozenset[str] = frozenset()
) -> ExposureAssessment:
    """Compute the exposure assessment for a resolved subject.

    Args:
        subject: The resolved dossier.
        disabled_axes: Surface axes to zero out (for ablation studies). Their
            weight is removed and the remaining weights are renormalized.
    """
    axis_scores = {name: func(subject) for name, func in _AXIS_FUNCS.items()}

    # Denominator is held at the full weight sum (1.0) so that disabling an axis
    # is a clean ablation: it removes exactly that axis's weighted contribution
    # rather than re-weighting the survivors (which could perversely raise the
    # score when a below-average axis is dropped).
    total_weight = sum(AXIS_WEIGHTS.values()) or 1.0
    base_surface = sum(
        axis_scores[name] * weight
        for name, weight in AXIS_WEIGHTS.items()
        if name not in disabled_axes
    ) / total_weight

    linkability_score = (
        0.0 if "linkability" in disabled_axes else _linkability(subject)
    )
    multiplier = 1.0 + ALPHA * (linkability_score / 100.0)
    score = min(100.0, base_surface * multiplier)

    ranked = sorted(axis_scores.items(), key=lambda kv: kv[1], reverse=True)
    top_factors = [_AXIS_LABELS[name] for name, value in ranked if value >= 25.0][:3]

    return ExposureAssessment(
        subject_id=subject.subject_id,
        score=round(score, 2),
        band=band_from_score(score),
        base_surface=round(base_surface, 2),
        linkability_multiplier=round(multiplier, 3),
        axis_scores={k: round(v, 2) for k, v in axis_scores.items()},
        linkability_score=round(linkability_score, 2),
        top_factors=top_factors,
    )
