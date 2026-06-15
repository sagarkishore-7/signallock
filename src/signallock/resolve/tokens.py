"""Token extraction: turn typed observations into typed guessing-material buckets.

This mirrors the wordlist-seeding step an attacker performs with CUPP/Mentalist:
names, org terms, dates, usernames, interests, and high-value personal trivia
(pets, family, affiliations) are each split into the atomic tokens a personalized
guess generator would mangle.
"""

from __future__ import annotations

import re

from ..core.enums import ATTRIBUTE_TO_BUCKET, AttributeKind, TokenBucket
from ..core.evidence import Observation

_SEP = re.compile(r"[\s._\-@/+]+")
_YEAR = re.compile(r"(19|20)\d{2}")


def _split_value(value: str, attr_kind: AttributeKind) -> list[str]:
    """Split one observation value into atomic, lowercased candidate tokens."""
    value = value.strip().lower()
    if not value:
        return []

    tokens: list[str] = []

    if attr_kind in (
        AttributeKind.TENURE_YEAR,
        AttributeKind.SIGNIFICANT_YEAR,
        AttributeKind.DATE_OF_BIRTH,
    ):
        # Keep full 4-digit years and their 2-digit suffix (e.g. 1994 -> 94).
        for match in _YEAR.finditer(value):
            year = match.group(0)
            tokens.append(year)
            tokens.append(year[2:])
        if not tokens and value.isdigit():
            tokens.append(value)
        return tokens

    if attr_kind is AttributeKind.EMAIL:
        local = value.split("@", 1)[0]
        tokens.extend(p for p in _SEP.split(local) if p)
        return tokens

    # General case: keep the whole phrase plus its word parts (both are useful
    # base words for mangling — "redsox" and "red", "sox").
    parts = [p for p in _SEP.split(value) if p]
    if len(parts) > 1:
        tokens.append("".join(parts))  # collapsed form, e.g. "red sox" -> "redsox"
    tokens.extend(parts)
    # Pull embedded years out of any value (e.g. a username "ghost94").
    for match in _YEAR.finditer(value):
        tokens.append(match.group(0))
    return tokens


def extract_token_buckets(
    observations: list[Observation],
) -> dict[TokenBucket, list[str]]:
    """Sort observations into typed token buckets, de-duplicated per bucket."""
    buckets: dict[TokenBucket, list[str]] = {bucket: [] for bucket in TokenBucket}
    for obs in observations:
        if obs.is_presence_only:
            continue
        bucket = ATTRIBUTE_TO_BUCKET.get(obs.attr_kind)
        if bucket is None:
            continue
        buckets[bucket].extend(_split_value(obs.value, obs.attr_kind))
    return buckets
