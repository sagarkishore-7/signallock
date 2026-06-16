"""Eidolon v2 — adversary-mirrored OSINT exposure and password predictability.

The public surface mirrors the attacker OSINT -> cracking kill chain:

    collect (Observations) -> resolve (Subject) -> exposure / predictability
    -> policy (HardeningRecommendation)

See ``docs/ADVERSARY_MIRROR.md`` for the defense-vs-offense mapping.
"""

from __future__ import annotations

from .core import (
    AttributeKind,
    Budget,
    ConsentedIdentity,
    ConsentError,
    ConsentRecord,
    ConsentRoster,
    HardeningAction,
    IdentitySeeds,
    Observation,
    RiskBand,
    RoleSeniority,
    SourceClass,
    Subject,
    TokenBucket,
    require_consent,
)
from .exposure import ExposureAssessment, assess_exposure
from .policy import HardeningRecommendation, recommend
from .predict import (
    BaselineStrength,
    ExposurePremium,
    PredictabilityAssessment,
    context_free_strength,
    exposure_premium,
    simulate_predictability,
)
from .resolve import resolve_subject

__version__ = "0.2.0"

__all__ = [
    "__version__",
    # core
    "AttributeKind",
    "Budget",
    "ConsentedIdentity",
    "ConsentError",
    "ConsentRecord",
    "ConsentRoster",
    "HardeningAction",
    "IdentitySeeds",
    "Observation",
    "RiskBand",
    "RoleSeniority",
    "SourceClass",
    "Subject",
    "TokenBucket",
    "require_consent",
    # pipeline
    "resolve_subject",
    "ExposureAssessment",
    "assess_exposure",
    "BaselineStrength",
    "ExposurePremium",
    "PredictabilityAssessment",
    "context_free_strength",
    "exposure_premium",
    "simulate_predictability",
    "HardeningRecommendation",
    "recommend",
]
