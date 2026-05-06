"""Template-based explanation renderer for SignalLock risk assessments."""

from __future__ import annotations

import json

from .schemas import (
    ExposureAssessment,
    ExposureExplanation,
    HardeningAction,
    HardeningExplanation,
    HardeningRecommendation,
    PasswordRiskAssessment,
    PasswordRiskExplanation,
    PublicProfile,
    RiskBand,
    RoleSeniority,
)


_SENIORITY_LABELS = {
    RoleSeniority.INDIVIDUAL_CONTRIBUTOR: "individual contributor",
    RoleSeniority.MANAGER: "manager",
    RoleSeniority.DIRECTOR: "director",
    RoleSeniority.VP: "vice president",
    RoleSeniority.C_SUITE: "executive",
}

_BAND_ADJECTIVES = {
    RiskBand.LOW: "low",
    RiskBand.MEDIUM: "moderate",
    RiskBand.HIGH: "high",
    RiskBand.CRITICAL: "critical",
}

_ACTION_SENTENCES = {
    HardeningAction.ALLOW: (
        "Based on the current assessment, no additional authentication action is required."
    ),
    HardeningAction.WARN: (
        "We recommend reviewing this password. The identified risk factors suggest it could be "
        "predicted by a targeted attacker, and a stronger choice would reduce exposure."
    ),
    HardeningAction.REQUIRE_STRONGER_PASSWORD: (
        "This password should be replaced. The combination of account visibility and password "
        "predictability creates meaningful targeted-attack risk that a stronger password would reduce."
    ),
    HardeningAction.ENFORCE_MFA: (
        "Multi-factor authentication should be enforced for this account. The account's public "
        "exposure is significant enough that password strength alone is insufficient protection."
    ),
    HardeningAction.STEP_UP_AUTHENTICATION: (
        "Step-up authentication should be required for sensitive operations. The exposure profile "
        "warrants additional verification beyond a standard password check."
    ),
    HardeningAction.PRIORITIZE_AWARENESS_TRAINING: (
        "This account should be prioritized for security awareness training. The elevated exposure "
        "profile increases the likelihood of targeted social engineering as well as password attacks."
    ),
}


def explain_exposure(
    assessment: ExposureAssessment,
    profile: PublicProfile,
) -> ExposureExplanation:
    """Produce a human-readable explanation of one exposure assessment."""
    band_label = _BAND_ADJECTIVES[assessment.band]
    seniority_label = _SENIORITY_LABELS[profile.role_seniority]
    summary = (
        f"{profile.full_name} ({profile.title} at {profile.organization}) "
        f"has a {band_label} exposure score of {assessment.score:.1f}/100."
    )

    factor_sentences = [
        _exposure_factor_sentence(factor, assessment, profile)
        for factor in assessment.top_factors
    ]

    return ExposureExplanation(
        employee_id=assessment.employee_id,
        exposure_score=assessment.score,
        exposure_band=assessment.band,
        summary=summary,
        factor_sentences=[s for s in factor_sentences if s],
    )


def explain_password_risk(
    assessment: PasswordRiskAssessment,
    profile: PublicProfile,
) -> PasswordRiskExplanation:
    """Produce a human-readable explanation of one password risk assessment."""
    band_label = _BAND_ADJECTIVES[assessment.band]
    summary = (
        f"The evaluated password scored {band_label} ({assessment.score:.1f}/100) "
        f"for targeted password risk against {profile.full_name}'s public profile context."
    )

    factor_sentences = [
        _password_factor_sentence(factor, assessment, profile)
        for factor in assessment.top_factors
    ]

    return PasswordRiskExplanation(
        employee_id=assessment.employee_id,
        password_score=assessment.score,
        password_band=assessment.band,
        summary=summary,
        factor_sentences=[s for s in factor_sentences if s],
    )


def explain_hardening(
    recommendation: HardeningRecommendation,
    exposure_explanation: ExposureExplanation,
    password_explanation: PasswordRiskExplanation,
) -> HardeningExplanation:
    """Combine exposure and password explanations into a full hardening explanation."""
    action_sentence = _ACTION_SENTENCES.get(
        recommendation.primary_action,
        f"The recommended action is {recommendation.primary_action.value}.",
    )

    parts: list[str] = [exposure_explanation.summary]
    if exposure_explanation.factor_sentences:
        parts.append(exposure_explanation.factor_sentences[0])
    parts.append(password_explanation.summary)
    if password_explanation.factor_sentences:
        parts.append(password_explanation.factor_sentences[0])
    parts.append(
        f"Given this combination, the recommended action is "
        f"{recommendation.primary_action.value}: {action_sentence}"
    )
    full_explanation = " ".join(parts)

    return HardeningExplanation(
        employee_id=recommendation.employee_id,
        primary_action=recommendation.primary_action,
        action_sentence=action_sentence,
        exposure_explanation=exposure_explanation,
        password_explanation=password_explanation,
        full_explanation=full_explanation,
    )


def explain_recommendation(
    recommendation: HardeningRecommendation,
    profile: PublicProfile,
    exposure: ExposureAssessment,
    password_risk: PasswordRiskAssessment,
) -> HardeningExplanation:
    """Convenience wrapper: produce a full explanation from all four inputs."""
    exposure_explanation = explain_exposure(exposure, profile)
    password_explanation = explain_password_risk(password_risk, profile)
    return explain_hardening(recommendation, exposure_explanation, password_explanation)


def explanation_to_json(explanation: HardeningExplanation, pretty: bool = False) -> str:
    """Serialize one hardening explanation as JSON."""
    payload = explanation.to_dict()
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


# --- exposure factor sentence builders ---

def _exposure_factor_sentence(
    factor: str,
    assessment: ExposureAssessment,
    profile: PublicProfile,
) -> str:
    seniority_label = _SENIORITY_LABELS[profile.role_seniority]

    if factor == "seniority visibility":
        return (
            f"As a {seniority_label} ({profile.title}), this account is a higher-priority "
            f"target for adversaries profiling {profile.organization}."
        )
    if factor == "public platform surface":
        count = profile.platform_count
        plural = "platforms" if count != 1 else "platform"
        return (
            f"The account is publicly present on {count} {plural}, giving a targeted attacker "
            f"multiple sources of context."
        )
    if factor == "public identity surface":
        usernames = profile.public_usernames[:2]
        if usernames:
            quoted = ", ".join(f'"{u}"' for u in usernames)
            return (
                f"The public username(s) {quoted} are discoverable and frequently "
                f"incorporated into targeted password guesses."
            )
        return (
            "Discoverable public identity information increases the likelihood of targeted guessing."
        )
    if factor == "public year markers":
        return (
            f"The tenure start year ({profile.tenure_start_year}) is publicly visible "
            f"and commonly appears in targeted password patterns."
        )
    if factor == "organization context richness":
        return (
            f"The listed role in the {profile.department} department at {profile.organization} "
            f"provides specific organizational context that attackers can use."
        )
    if factor == "context richness":
        parts: list[str] = []
        if profile.location:
            parts.append(profile.location)
        if profile.interests:
            parts.append(", ".join(profile.interests[:2]))
        context_str = " and ".join(parts) if parts else "public interests and location"
        return (
            f"Publicly listed details ({context_str}) provide additional context "
            f"that targeted attackers can use to narrow guesses."
        )
    if factor == "high-discoverability platform presence":
        return (
            "This profile appears on high-discoverability sources such as a personal website, "
            "speaker bio, or company directory, making it straightforward to locate."
        )
    return ""


# --- password risk factor sentence builders ---

def _password_factor_sentence(
    factor: str,
    assessment: PasswordRiskAssessment,
    profile: PublicProfile,
) -> str:
    if factor == "short password length":
        return (
            f"At {assessment.password_length} characters, the password is short, "
            f"reducing the guessing effort required in a targeted attack."
        )
    if factor == "low character diversity":
        return (
            "The password uses a limited mix of character types, reducing its resistance "
            "to targeted guessing."
        )
    if factor == "simple sequence or common pattern":
        return (
            "The password contains a common sequence or dictionary pattern that appears "
            "early in targeted guess lists."
        )
    if factor == "repetition pattern":
        return (
            "The password contains repeated characters, a recognizable weakness "
            "in targeted attacks."
        )
    if factor == "name overlap":
        matched = assessment.matched_tokens.get("name_tokens", [])
        token_str = _quoted_tokens(matched)
        return (
            f"The password contains tokens matching the account holder's name "
            f"({token_str or 'name-derived tokens'}), "
            f"which a targeted attacker would try early."
        )
    if factor == "organization overlap":
        matched = assessment.matched_tokens.get("organization_tokens", [])
        token_str = _quoted_tokens(matched)
        return (
            f"The password contains tokens linked to the organization or role "
            f"({token_str or 'organization-derived tokens'}), "
            f"providing a targeted attacker with a useful starting point."
        )
    if factor == "public year marker overlap":
        matched = assessment.matched_tokens.get("temporal_tokens", [])
        token_str = _quoted_tokens(matched)
        return (
            f"The password contains a publicly visible year marker "
            f"({token_str or profile.tenure_start_year}), "
            f"a pattern targeted attackers commonly try first."
        )
    if factor == "public username overlap":
        matched = assessment.matched_tokens.get("identity_tokens", [])
        token_str = _quoted_tokens(matched)
        return (
            f"The password contains tokens from a public username "
            f"({token_str or 'identity-derived tokens'}), "
            f"making it predictable to anyone who has found the account online."
        )
    if factor == "interest or location overlap":
        matched = assessment.matched_tokens.get("context_tokens", [])
        token_str = _quoted_tokens(matched)
        return (
            f"The password contains words from publicly listed interests or location "
            f"({token_str or 'context-derived tokens'}), "
            f"which a targeted attacker can derive from the public profile."
        )
    if factor == "contextual structure pattern":
        return (
            "The password follows a predictable structure combining personal context "
            "(such as a name or organisation token) with a year — one of the most "
            "common patterns in targeted guessing attacks."
        )
    return ""


def _quoted_tokens(tokens: list[str], limit: int = 3) -> str:
    """Render up to `limit` tokens as a readable quoted list."""
    selected = tokens[:limit]
    if not selected:
        return ""
    return ", ".join(f'"{t}"' for t in selected)
