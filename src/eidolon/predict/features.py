"""Feature extraction for the learned predictability model.

Combines exposure sub-scores, typed token-bucket counts, generic password
structure, and the zxcvbn baseline into a fixed, ordered feature vector. The
learned model uses these to predict the simulator's budget-bucket label without
running the full simulation at inference time.
"""

from __future__ import annotations

from ..core.enums import TokenBucket
from ..core.subject import Subject
from ..exposure.model import ExposureAssessment
from .baseline import BaselineStrength

#: Stable, ordered feature names. Anything appended must go at the end.
FEATURE_NAMES: list[str] = [
    # exposure
    "exposure_score",
    "exposure_base_surface",
    "exposure_linkability_multiplier",
    "exposure_linkability_score",
    "axis_discoverability",
    "axis_professional_visibility",
    "axis_personal_trivia_richness",
    "axis_breach_exposure",
    "axis_temporal_footprint",
    # subject token-bucket counts
    "tok_name",
    "tok_organization",
    "tok_temporal",
    "tok_identity",
    "tok_location",
    "tok_interest",
    "tok_personal_trivia",
    "tok_structure_prior",
    "platform_count",
    "breach_count",
    # generic password structure
    "pw_length",
    "pw_digit_ratio",
    "pw_upper_ratio",
    "pw_symbol_ratio",
    "pw_unique_ratio",
    "pw_has_year",
    # contextual overlap: does THIS password derive from the subject's tokens?
    # (the signal the simulator exploits, computed without running it)
    "ctx_name_overlap",
    "ctx_personal_trivia_overlap",
    "ctx_temporal_overlap",
    "ctx_identity_overlap",
    "ctx_organization_overlap",
    "ctx_interest_overlap",
    "ctx_any_overlap",
    "ctx_longest_match_ratio",
    # baseline
    "baseline_guesses_log10",
    "baseline_zxcvbn_score",
]

#: Buckets whose overlap with the password is measured as a contextual feature.
_OVERLAP_BUCKETS: list[tuple[str, TokenBucket]] = [
    ("ctx_name_overlap", TokenBucket.NAME),
    ("ctx_personal_trivia_overlap", TokenBucket.PERSONAL_TRIVIA),
    ("ctx_temporal_overlap", TokenBucket.TEMPORAL),
    ("ctx_identity_overlap", TokenBucket.IDENTITY),
    ("ctx_organization_overlap", TokenBucket.ORGANIZATION),
    ("ctx_interest_overlap", TokenBucket.INTEREST),
]

_SYMBOLS = set("!@#$%^&*()_+-=[]{};:,.<>?/|\\`~'\"")


def _password_features(password: str) -> dict[str, float]:
    length = len(password) or 1
    digits = sum(c.isdigit() for c in password)
    uppers = sum(c.isupper() for c in password)
    symbols = sum(c in _SYMBOLS for c in password)
    unique = len(set(password))
    has_year = 1.0 if any(
        password[i : i + 4].isdigit() and password[i : i + 2] in ("19", "20")
        for i in range(max(0, len(password) - 3))
    ) else 0.0
    return {
        "pw_length": float(len(password)),
        "pw_digit_ratio": digits / length,
        "pw_upper_ratio": uppers / length,
        "pw_symbol_ratio": symbols / length,
        "pw_unique_ratio": unique / length,
        "pw_has_year": has_year,
    }


def _contextual_features(subject: Subject, password: str) -> dict[str, float]:
    """Overlap between the password and the subject's typed tokens.

    For each bucket, the fraction of its tokens (length >= 3) that appear as a
    substring of the lowercased password. ``ctx_longest_match_ratio`` is the
    longest matched token length over the password length. These mirror the
    attacker's wordlist hits without running the full guess simulation.
    """
    pw = password.lower()
    pw_len = len(password) or 1
    features: dict[str, float] = {}
    longest = 0
    any_overlap = 0.0
    for name, bucket in _OVERLAP_BUCKETS:
        tokens = [t for t in subject.tokens(bucket) if len(t) >= 3]
        hits = [t for t in tokens if t in pw]
        ratio = (len(hits) / len(tokens)) if tokens else 0.0
        features[name] = ratio
        any_overlap = max(any_overlap, ratio)
        longest = max([longest] + [len(t) for t in hits])
    features["ctx_any_overlap"] = any_overlap
    features["ctx_longest_match_ratio"] = longest / pw_len
    return features


def build_features(
    subject: Subject,
    exposure: ExposureAssessment,
    password: str,
    baseline: BaselineStrength,
) -> dict[str, float]:
    """Build the named feature dictionary for one (subject, password) pair."""
    axes = exposure.axis_scores
    features: dict[str, float] = {
        "exposure_score": exposure.score,
        "exposure_base_surface": exposure.base_surface,
        "exposure_linkability_multiplier": exposure.linkability_multiplier,
        "exposure_linkability_score": exposure.linkability_score,
        "axis_discoverability": axes["discoverability"],
        "axis_professional_visibility": axes["professional_visibility"],
        "axis_personal_trivia_richness": axes["personal_trivia_richness"],
        "axis_breach_exposure": axes["breach_exposure"],
        "axis_temporal_footprint": axes["temporal_footprint"],
        "tok_name": float(len(subject.tokens(TokenBucket.NAME))),
        "tok_organization": float(len(subject.tokens(TokenBucket.ORGANIZATION))),
        "tok_temporal": float(len(subject.tokens(TokenBucket.TEMPORAL))),
        "tok_identity": float(len(subject.tokens(TokenBucket.IDENTITY))),
        "tok_location": float(len(subject.tokens(TokenBucket.LOCATION))),
        "tok_interest": float(len(subject.tokens(TokenBucket.INTEREST))),
        "tok_personal_trivia": float(
            len(subject.tokens(TokenBucket.PERSONAL_TRIVIA))
        ),
        "tok_structure_prior": float(
            len(subject.tokens(TokenBucket.STRUCTURE_PRIOR))
        ),
        "platform_count": float(subject.platform_count),
        "breach_count": float(subject.breach_count),
        "baseline_guesses_log10": baseline.guesses_log10,
        "baseline_zxcvbn_score": float(baseline.zxcvbn_score),
    }
    features.update(_password_features(password))
    features.update(_contextual_features(subject, password))
    return features


def feature_row(features: dict[str, float]) -> list[float]:
    """Project a feature dict onto the stable ordered vector."""
    return [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
