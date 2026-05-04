"""Baseline password-risk assessment conditioned on public profile context."""

from __future__ import annotations

import json
import re

from .exposure import profile_to_attribute_vector
from .schemas import AttributeVector, PasswordRiskAssessment, PublicProfile, RiskBand


SEQUENCE_MARKERS = ("123", "234", "345", "abc", "qwerty", "password", "admin")

GENERIC_LABELS = {
    "short_length": "short password length",
    "low_diversity": "low character diversity",
    "simple_sequence": "simple sequence or common pattern",
    "repetition_pattern": "repetition pattern",
}

CONTEXT_LABELS = {
    "name_overlap": "name overlap",
    "organization_overlap": "organization overlap",
    "temporal_overlap": "public year marker overlap",
    "identity_overlap": "public username overlap",
    "context_overlap": "interest or location overlap",
    "contextual_structure": "contextual structure pattern",
}


def _band_for_score(score: float) -> RiskBand:
    """Map a numeric score to a bounded risk band."""
    if score < 25.0:
        return RiskBand.LOW
    if score < 50.0:
        return RiskBand.MEDIUM
    if score < 75.0:
        return RiskBand.HIGH
    return RiskBand.CRITICAL


def _character_class_count(password: str) -> int:
    """Count distinct character classes present in a password."""
    classes = 0
    if any(char.islower() for char in password):
        classes += 1
    if any(char.isupper() for char in password):
        classes += 1
    if any(char.isdigit() for char in password):
        classes += 1
    if any(not char.isalnum() for char in password):
        classes += 1
    return classes


def _find_token_matches(password_lower: str, tokens: list[str], min_length: int) -> list[str]:
    """Find normalized token overlaps in a password."""
    matches: list[str] = []
    seen: set[str] = set()

    for token in tokens:
        normalized = token.lower().strip()
        if len(normalized) < min_length:
            continue
        if normalized in password_lower and normalized not in seen:
            seen.add(normalized)
            matches.append(normalized)

    return matches


def score_password_for_vector(
    password: str,
    vector: AttributeVector,
) -> PasswordRiskAssessment:
    """Score a candidate password against a normalized attribute vector."""
    if not password:
        raise ValueError("password must be non-empty")

    password_lower = password.lower()
    length = len(password)
    class_count = _character_class_count(password)

    generic_signals = {
        "short_length": 30.0
        if length < 8
        else 22.0
        if length < 10
        else 14.0
        if length < 12
        else 7.0
        if length < 14
        else 0.0,
        "low_diversity": 18.0 if class_count <= 1 else 12.0 if class_count == 2 else 6.0 if class_count == 3 else 0.0,
        "simple_sequence": 10.0 if any(marker in password_lower for marker in SEQUENCE_MARKERS) else 0.0,
        "repetition_pattern": 8.0 if re.search(r"(.)\1\1", password_lower) else 0.0,
    }

    matched_tokens = {
        "name_tokens": _find_token_matches(password_lower, vector.name_tokens, min_length=3),
        "organization_tokens": _find_token_matches(password_lower, vector.organization_tokens, min_length=4),
        "temporal_tokens": _find_token_matches(password_lower, vector.temporal_tokens, min_length=4),
        "identity_tokens": _find_token_matches(password_lower, vector.identity_tokens, min_length=4),
        "context_tokens": _find_token_matches(password_lower, vector.context_tokens, min_length=4),
    }

    contextual_signals = {
        "name_overlap": min(len(matched_tokens["name_tokens"]) * 12.0, 30.0),
        "organization_overlap": min(len(matched_tokens["organization_tokens"]) * 8.0, 18.0),
        "temporal_overlap": 12.0 if matched_tokens["temporal_tokens"] else 0.0,
        "identity_overlap": min(len(matched_tokens["identity_tokens"]) * 10.0, 20.0),
        "context_overlap": min(len(matched_tokens["context_tokens"]) * 5.0, 12.0),
        "contextual_structure": 12.0
        if matched_tokens["name_tokens"] and matched_tokens["temporal_tokens"]
        else 8.0
        if matched_tokens["organization_tokens"] and matched_tokens["temporal_tokens"]
        else 0.0,
    }

    score = round(min(100.0, sum(generic_signals.values()) + sum(contextual_signals.values())), 2)
    band = _band_for_score(score)

    factor_weights = list(generic_signals.items()) + list(contextual_signals.items())
    top_factors = []
    for key, value in sorted(factor_weights, key=lambda item: item[1], reverse=True):
        if value <= 0.0:
            continue
        label = GENERIC_LABELS.get(key, CONTEXT_LABELS.get(key, key))
        top_factors.append(label)
        if len(top_factors) == 3:
            break

    return PasswordRiskAssessment(
        employee_id=vector.employee_id,
        password_length=length,
        score=score,
        band=band,
        generic_signals={key: round(value, 2) for key, value in generic_signals.items()},
        contextual_signals={key: round(value, 2) for key, value in contextual_signals.items()},
        matched_tokens=matched_tokens,
        top_factors=top_factors,
    )


def score_password_for_profile(password: str, profile: PublicProfile) -> PasswordRiskAssessment:
    """Score a password against a full public profile."""
    vector = profile_to_attribute_vector(profile)
    return score_password_for_vector(password, vector)


def assessment_to_json(assessment: PasswordRiskAssessment, pretty: bool = False) -> str:
    """Serialize one password-risk assessment as JSON."""
    payload = assessment.to_dict()
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
