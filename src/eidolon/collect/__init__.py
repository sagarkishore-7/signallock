"""The adversary-mirrored collection layer.

Each collector in this package is the defensive mirror of one attacker OSINT
tool. Importing the package registers every collector in :data:`MIRROR_REGISTRY`
(via the :func:`register` decorator) so :func:`adversary_mirror_table` can render
the collector→attacker-tool mapping that drives ``docs/ADVERSARY_MIRROR.md``.

All collectors run behind the same hard consent gate (``Collector.collect`` calls
``require_consent`` first) and emit typed :class:`~eidolon.core.evidence.Observation`
records, never flattened profiles or raw scraped text.
"""

from __future__ import annotations

from .base import (
    Collector,
    MIRROR_REGISTRY,
    adversary_mirror_table,
    register,
)
from .breach_intel import BreachIntel
from .code_profile import CodeProfile
from .email_enum import EmailEnumerator
from .footprint import FootprintSearch
from .professional import ProfessionalProfile
from .public_records import PublicRecords
from .snapshot import SnapshotCollector, load_snapshot
from .social import SocialProfile
from .username_enum import UsernameEnumerator
from .web_profile import WebProfile

__all__ = [
    "Collector",
    "MIRROR_REGISTRY",
    "register",
    "adversary_mirror_table",
    "load_snapshot",
    "SnapshotCollector",
    "BreachIntel",
    "CodeProfile",
    "EmailEnumerator",
    "FootprintSearch",
    "ProfessionalProfile",
    "PublicRecords",
    "SocialProfile",
    "UsernameEnumerator",
    "WebProfile",
]
