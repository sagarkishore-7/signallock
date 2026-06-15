"""Personalized guess generation — the defensive mirror of CUPP / TarGuess.

Given a resolved :class:`Subject`, this yields candidate passwords in roughly
increasing attacker effort, applying the same transforms a personalized wordlist
tool would: casing, common affixes, leet substitution, and token concatenation,
biased toward the subject's high-value personal trivia.

This module is dual-use. It is exercised only by the consent-gated
:mod:`signallock.predict.simulator`, which never emits the generated strings —
only the matched template *category* and the budget at which a match occurred.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ..core.enums import TokenBucket
from ..core.subject import Subject

# Buckets ordered by how strongly a targeted attacker would prioritize them.
_BASE_BUCKET_PRIORITY = (
    TokenBucket.STRUCTURE_PRIOR,   # prior breached passwords / habits
    TokenBucket.PERSONAL_TRIVIA,   # pets, family, teams
    TokenBucket.NAME,
    TokenBucket.IDENTITY,
    TokenBucket.INTEREST,
    TokenBucket.ORGANIZATION,
    TokenBucket.LOCATION,
)

_COMMON_SUFFIXES = ("1", "123", "!", "12", "01", "1234", "@", "#", "2024", "2025")
_LEET = str.maketrans({"a": "@", "e": "3", "i": "1", "o": "0", "s": "$"})


@dataclass(frozen=True)
class GuessCandidate:
    """One generated candidate plus the template category that produced it."""

    value: str
    category: str  # "base" | "case" | "affix" | "leet" | "combo"


def _base_words(subject: Subject) -> list[str]:
    """Ordered, de-duplicated base words biased to high-value buckets."""
    words: list[str] = []
    seen: set[str] = set()
    for bucket in _BASE_BUCKET_PRIORITY:
        for token in subject.tokens(bucket):
            if len(token) >= 2 and token not in seen:
                seen.add(token)
                words.append(token)
    return words


def _years(subject: Subject) -> list[str]:
    """Subject-derived temporal affixes (full and 2-digit years)."""
    return [t for t in subject.tokens(TokenBucket.TEMPORAL) if t.isdigit()]


def generate_guesses(subject: Subject, *, limit: int) -> Iterator[GuessCandidate]:
    """Yield up to ``limit`` unique candidates in increasing-effort order."""
    seen: set[str] = set()
    count = 0
    base = _base_words(subject)
    suffixes = _years(subject) + list(_COMMON_SUFFIXES)

    def emit(value: str, category: str) -> Iterator[GuessCandidate]:
        nonlocal count
        if count >= limit:
            return
        if value and value not in seen:
            seen.add(value)
            count += 1
            yield GuessCandidate(value, category)

    # Tier 1 — raw and simple casing.
    for word in base:
        if count >= limit:
            return
        yield from emit(word, "base")
        yield from emit(word.capitalize(), "case")
        yield from emit(word.upper(), "case")

    # Tier 2 — base + common/temporal affixes (and capitalized variants).
    for word in base:
        for suffix in suffixes:
            if count >= limit:
                return
            yield from emit(word + suffix, "affix")
            yield from emit(word.capitalize() + suffix, "affix")

    # Tier 3 — leet substitutions of base and affixed forms.
    for word in base:
        leet = word.translate(_LEET)
        if leet == word:
            continue
        if count >= limit:
            return
        yield from emit(leet, "leet")
        for suffix in suffixes:
            if count >= limit:
                return
            yield from emit(leet + suffix, "leet")

    # Tier 4 — pairwise concatenations (e.g. pet+team, name+year), then affixed.
    for i, first in enumerate(base):
        for second in base[i + 1 :]:
            if count >= limit:
                return
            yield from emit(first + second, "combo")
            yield from emit(first.capitalize() + second.capitalize(), "combo")
            for suffix in suffixes:
                if count >= limit:
                    return
                yield from emit(first + second + suffix, "combo")
