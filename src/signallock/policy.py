"""Baseline policy engine for turning risk scores into hardening actions."""

from __future__ import annotations

import json

from .schemas import (
    ExposureAssessment,
    HardeningAction,
    HardeningRecommendation,
    PasswordRiskAssessment,
    RiskBand,
)


def _append_unique(actions: list[HardeningAction], action: HardeningAction) -> None:
    """Add an action once while preserving order."""
    if action not in actions:
        actions.append(action)


def recommend_hardening(
    exposure: ExposureAssessment,
    password_risk: PasswordRiskAssessment,
) -> HardeningRecommendation:
    """Combine exposure and password risk into a baseline hardening recommendation."""
    if exposure.employee_id != password_risk.employee_id:
        raise ValueError("exposure and password_risk must refer to the same employee_id")

    combined_score = round((exposure.score * 0.4) + (password_risk.score * 0.6), 2)
    supporting_actions: list[HardeningAction] = []
    rationale: list[str] = []

    if exposure.band in {RiskBand.HIGH, RiskBand.CRITICAL}:
        _append_unique(supporting_actions, HardeningAction.PRIORITIZE_AWARENESS_TRAINING)
    if exposure.band == RiskBand.CRITICAL or combined_score >= 75.0:
        _append_unique(supporting_actions, HardeningAction.ENFORCE_MFA)
    elif exposure.band == RiskBand.HIGH or combined_score >= 55.0:
        _append_unique(supporting_actions, HardeningAction.STEP_UP_AUTHENTICATION)

    if password_risk.band == RiskBand.CRITICAL:
        primary_action = HardeningAction.REQUIRE_STRONGER_PASSWORD
    elif password_risk.band == RiskBand.HIGH and exposure.band in {RiskBand.HIGH, RiskBand.CRITICAL}:
        primary_action = HardeningAction.REQUIRE_STRONGER_PASSWORD
    elif exposure.band == RiskBand.CRITICAL:
        primary_action = HardeningAction.ENFORCE_MFA
    elif exposure.band == RiskBand.HIGH:
        primary_action = HardeningAction.STEP_UP_AUTHENTICATION
    elif password_risk.band == RiskBand.HIGH:
        primary_action = HardeningAction.WARN
    elif password_risk.band == RiskBand.MEDIUM or combined_score >= 40.0:
        primary_action = HardeningAction.WARN
    else:
        primary_action = HardeningAction.ALLOW

    supporting_actions = [action for action in supporting_actions if action != primary_action]

    rationale.extend(exposure.top_factors[:2])
    rationale.extend(password_risk.top_factors[:2])

    seen_rationale: set[str] = set()
    deduped_rationale: list[str] = []
    for item in rationale:
        if item in seen_rationale:
            continue
        seen_rationale.add(item)
        deduped_rationale.append(item)

    return HardeningRecommendation(
        employee_id=exposure.employee_id,
        exposure_score=exposure.score,
        exposure_band=exposure.band,
        password_score=password_risk.score,
        password_band=password_risk.band,
        combined_score=combined_score,
        primary_action=primary_action,
        supporting_actions=supporting_actions,
        rationale=deduped_rationale[:4],
    )


def recommendation_to_json(
    recommendation: HardeningRecommendation,
    pretty: bool = False,
) -> str:
    """Serialize one hardening recommendation as JSON."""
    payload = recommendation.to_dict()
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
