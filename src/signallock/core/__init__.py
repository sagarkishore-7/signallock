"""SignalLock v2 core: enums, consent spine, evidence, and resolved subjects."""

from __future__ import annotations

from .enums import (
    ATTRIBUTE_TO_BUCKET,
    BUDGET_TO_BAND,
    AttributeKind,
    Budget,
    HardeningAction,
    RiskBand,
    RoleSeniority,
    SourceClass,
    TokenBucket,
)
from .errors import (
    CollectorError,
    ConsentError,
    DependencyError,
    SignalLockError,
    require_dependency,
)
from .evidence import Observation
from .identity import (
    ConsentedIdentity,
    ConsentRecord,
    ConsentRoster,
    IdentitySeeds,
    require_consent,
)
from .subject import Subject

__all__ = [
    "ATTRIBUTE_TO_BUCKET",
    "BUDGET_TO_BAND",
    "AttributeKind",
    "Budget",
    "HardeningAction",
    "RiskBand",
    "RoleSeniority",
    "SourceClass",
    "TokenBucket",
    "CollectorError",
    "ConsentError",
    "DependencyError",
    "SignalLockError",
    "require_dependency",
    "Observation",
    "ConsentedIdentity",
    "ConsentRecord",
    "ConsentRoster",
    "IdentitySeeds",
    "require_consent",
    "Subject",
]
