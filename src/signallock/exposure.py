"""Public-profile normalization and baseline exposure scoring."""

from __future__ import annotations

import json
import re

from .schemas import AttributeVector, ExposureAssessment, Platform, PublicProfile, RiskBand, RoleSeniority


TOKEN_RE = re.compile(r"[a-z0-9]+")

SENIORITY_WEIGHTS = {
    RoleSeniority.INDIVIDUAL_CONTRIBUTOR: 8.0,
    RoleSeniority.MANAGER: 15.0,
    RoleSeniority.DIRECTOR: 24.0,
    RoleSeniority.VP: 30.0,
    RoleSeniority.C_SUITE: 35.0,
}

DISCOVERABILITY_PLATFORMS = {
    Platform.COMPANY_DIRECTORY,
    Platform.PERSONAL_WEBSITE,
    Platform.SPEAKER_BIO,
}

COMPONENT_LABELS = {
    "seniority_visibility": "seniority visibility",
    "platform_surface": "public platform surface",
    "public_identity_surface": "public identity surface",
    "temporal_surface": "public year markers",
    "organization_context": "organization context richness",
    "contextual_surface": "context richness",
    "discoverability_bonus": "high-discoverability platform presence",
}


def _tokenize_text(value: str) -> list[str]:
    """Split free text into lowercase alphanumeric tokens."""
    return TOKEN_RE.findall(value.lower())


def profile_to_attribute_vector(profile: PublicProfile) -> AttributeVector:
    """Normalize a public profile into a model-friendly attribute vector."""
    name_tokens = _tokenize_text(profile.full_name)
    if profile.preferred_name:
        name_tokens.extend(_tokenize_text(profile.preferred_name))

    organization_tokens = (
        _tokenize_text(profile.organization)
        + _tokenize_text(profile.department)
        + _tokenize_text(profile.title)
    )

    temporal_tokens = [str(profile.tenure_start_year)]

    identity_tokens = list(profile.public_usernames)
    identity_tokens.append(profile.email_format)

    context_tokens = _tokenize_text(profile.location)
    context_tokens.extend(profile.interests)
    if profile.education:
        context_tokens.extend(_tokenize_text(profile.education))

    return AttributeVector(
        employee_id=profile.employee_id,
        role_seniority=profile.role_seniority,
        name_tokens=name_tokens,
        organization_tokens=organization_tokens,
        temporal_tokens=temporal_tokens,
        identity_tokens=identity_tokens,
        context_tokens=context_tokens,
        platform_count=profile.platform_count,
    )


def _band_for_score(score: float) -> RiskBand:
    """Map a numeric score to a bounded risk band."""
    if score < 30.0:
        return RiskBand.LOW
    if score < 55.0:
        return RiskBand.MEDIUM
    if score < 75.0:
        return RiskBand.HIGH
    return RiskBand.CRITICAL


def score_exposure(profile: PublicProfile) -> ExposureAssessment:
    """Compute a transparent baseline exposure score for one profile."""
    vector = profile_to_attribute_vector(profile)

    component_scores = {
        "seniority_visibility": SENIORITY_WEIGHTS[profile.role_seniority],
        "platform_surface": min(vector.platform_count, 4) / 4.0 * 20.0,
        "public_identity_surface": min(len(profile.public_usernames), 2) / 2.0 * 10.0,
        "temporal_surface": min(len(vector.temporal_tokens), 2) / 2.0 * 8.0,
        "organization_context": min(len(vector.organization_tokens), 6) / 6.0 * 12.0,
        "contextual_surface": min(len(vector.context_tokens), 8) / 8.0 * 10.0,
        "discoverability_bonus": 5.0
        if any(platform in DISCOVERABILITY_PLATFORMS for platform in profile.platforms)
        else 0.0,
    }

    score = round(sum(component_scores.values()), 2)
    band = _band_for_score(score)

    ranked_components = sorted(
        component_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    top_factors = [
        COMPONENT_LABELS[name]
        for name, value in ranked_components
        if value > 0.0
    ][:3]

    return ExposureAssessment(
        employee_id=profile.employee_id,
        score=score,
        band=band,
        component_scores={key: round(value, 2) for key, value in component_scores.items()},
        top_factors=top_factors,
    )


def score_profiles_exposure(profiles: list[PublicProfile]) -> list[ExposureAssessment]:
    """Score a batch of public profiles."""
    return [score_exposure(profile) for profile in profiles]


def assessments_to_json(assessments: list[ExposureAssessment], pretty: bool = False) -> str:
    """Serialize exposure assessments as JSON."""
    payload = [assessment.to_dict() for assessment in assessments]
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
