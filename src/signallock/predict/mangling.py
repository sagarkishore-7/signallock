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
from datetime import datetime, timezone

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

# Per-bucket caps on base words. High-value buckets are used in full; noisy,
# low-value buckets (e.g. INTEREST from public repo names/topics) are capped so a
# long tail of weak tokens cannot dilute the guess ranking under a bounded budget.
_BASE_BUCKET_CAPS = {
    TokenBucket.INTEREST: 12,
    TokenBucket.ORGANIZATION: 8,
    TokenBucket.LOCATION: 4,
}

# Common number/symbol affixes, ordered by real-world frequency (breach studies)
# so the bounded budget spends on the most likely guesses first.
_COMMON_AFFIXES = (
    "1", "123", "12", "2", "11", "21", "69", "07", "00", "99", "13", "23",
    "321", "1234", "12345", "007", "01", "!", "@", "#", "$",
)
#: How many years back the dynamic year window reaches (covers plausible birth,
#: graduation, and tenure years without hardcoding specific years).
_YEAR_LOOKBACK = 50
#: The most recent N years lead the affix order — recent years are among the
#: highest-frequency password suffixes, so they precede generic numbers/symbols.
_RECENT_YEARS = 8
_LEET = str.maketrans({"a": "@", "e": "3", "i": "1", "o": "0", "s": "$"})


@dataclass(frozen=True)
class GuessCandidate:
    """One generated candidate plus the template category that produced it."""

    value: str
    category: str  # "base" | "case" | "affix" | "leet" | "combo"


def _base_words(subject: Subject) -> list[str]:
    """Ordered, de-duplicated base words biased to high-value buckets, with noisy
    low-value buckets capped (see ``_BASE_BUCKET_CAPS``)."""
    words: list[str] = []
    seen: set[str] = set()
    for bucket in _BASE_BUCKET_PRIORITY:
        cap = _BASE_BUCKET_CAPS.get(bucket)
        taken = 0
        for token in subject.tokens(bucket):
            if len(token) >= 2 and token not in seen:
                seen.add(token)
                words.append(token)
                taken += 1
                if cap is not None and taken >= cap:
                    break
    return words


def _affixes(subject: Subject) -> list[str]:
    """Ordered affixes, common-first, so a bounded budget tries likely guesses
    first: the subject's own OSINT years (an attacker knows these), then common
    number/symbol suffixes, then a dynamic recent-year window. De-hardcoded so it
    never goes stale and does not arbitrarily privilege two specific years.
    """
    osint_years = [t for t in subject.tokens(TokenBucket.TEMPORAL) if t.isdigit()]
    now = datetime.now(timezone.utc).year
    recent_years = [str(y) for y in range(now + 1, now - _RECENT_YEARS, -1)]
    older_years = [str(y) for y in range(now - _RECENT_YEARS, now - _YEAR_LOOKBACK, -1)]
    ordered: list[str] = []
    seen: set[str] = set()
    for affix in (*osint_years, *recent_years, *_COMMON_AFFIXES, *older_years):
        if affix not in seen:
            seen.add(affix)
            ordered.append(affix)
    return ordered


def generate_guesses(subject: Subject, *, limit: int) -> Iterator[GuessCandidate]:
    """Yield up to ``limit`` unique candidates in increasing-effort order."""
    seen: set[str] = set()
    count = 0
    base = _base_words(subject)
    suffixes = _affixes(subject)

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

    # Tier 2 — base + affixes, affix-major: the most common affixes are tried
    # across all base words first, so a bounded budget reaches the likeliest
    # (token, affix) combos regardless of how many tokens the dossier has.
    for suffix in suffixes:
        for word in base:
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
