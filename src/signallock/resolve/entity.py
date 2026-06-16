"""Entity resolution: merge observations for one identity into a Subject.

The resolver is the defensive mirror of an attacker's identity-resolution step
(Maltego/SpiderFoot): scattered findings from many sources are fused into a
single dossier, recording which platforms resolved the subject and how much each
source yielded (the depth signal the exposure model consumes).
"""

from __future__ import annotations

from collections import defaultdict

from ..core.enums import AttributeKind, RoleSeniority, SourceClass, Visibility
from ..core.evidence import Observation
from ..core.subject import Subject
from .tokens import extract_token_buckets


def filter_by_visibility(
    observations: list[Observation], max_visibility: Visibility
) -> list[Observation]:
    """Keep observations reachable at or below ``max_visibility``.

    ``PUBLIC`` keeps only fully-public data; ``GATED`` additionally keeps
    connection-gated data; ``PRIVATE`` keeps everything. This lets exposure and
    predictability be scored for a fully-public attacker versus one who has
    connected to (or follows) the subject.
    """
    return [o for o in observations if o.visibility.rank <= max_visibility.rank]


def _resolve_seniority(observations: list[Observation]) -> RoleSeniority:
    """Pick the highest seniority asserted by any ROLE_TITLE observation.

    A role observation may carry an explicit seniority token (e.g. "DIRECTOR")
    or a title we map heuristically. Unknown titles default to IC.
    """
    best = RoleSeniority.INDIVIDUAL_CONTRIBUTOR
    for obs in observations:
        if obs.attr_kind is not AttributeKind.ROLE_TITLE:
            continue
        seniority = _title_to_seniority(obs.value)
        if seniority.rank > best.rank:
            best = seniority
    return best


_TITLE_HINTS: list[tuple[tuple[str, ...], RoleSeniority]] = [
    (("chief", "ceo", "cto", "cfo", "ciso", "founder", "c-suite"), RoleSeniority.C_SUITE),
    (("vp", "vice president"), RoleSeniority.VP),
    (("director", "head of"), RoleSeniority.DIRECTOR),
    (("manager", "lead", "principal"), RoleSeniority.MANAGER),
]


def _title_to_seniority(value: str) -> RoleSeniority:
    text = value.strip().lower()
    # Allow direct enum names in snapshots, e.g. "VP".
    for member in RoleSeniority:
        if text == member.value.lower():
            return member
    for hints, seniority in _TITLE_HINTS:
        if any(hint in text for hint in hints):
            return seniority
    return RoleSeniority.INDIVIDUAL_CONTRIBUTOR


def resolve_subject(
    subject_id: str, observations: list[Observation]
) -> Subject:
    """Merge all observations about ``subject_id`` into a resolved Subject."""
    relevant = [obs for obs in observations if obs.subject_id == subject_id]

    token_buckets = extract_token_buckets(relevant)

    # Per-source depth = count of distinct attribute kinds harvested there.
    coverage_kinds: dict[SourceClass, set[AttributeKind]] = defaultdict(set)
    breaches: set[str] = set()
    for obs in relevant:
        coverage_kinds[obs.source].add(obs.attr_kind)
        if obs.attr_kind is AttributeKind.BREACH:
            breaches.add(obs.value.lower())

    source_coverage = {src: len(kinds) for src, kinds in coverage_kinds.items()}
    platforms = sorted(coverage_kinds, key=lambda s: s.value)

    return Subject(
        subject_id=subject_id,
        role_seniority=_resolve_seniority(relevant),
        token_buckets=token_buckets,
        platforms=platforms,
        source_coverage=source_coverage,
        breach_count=len(breaches),
    )
