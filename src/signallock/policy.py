"""Baseline policy engine for turning risk scores into hardening actions."""

from __future__ import annotations

import json

from .schemas import (
    ExposureAssessment,
    HardeningAction,
    HardeningRecommendation,
    PasswordRiskAssessment,
    PolicyConfig,
    PolicyProfile,
    RiskBand,
)


BAND_RANK = {
    RiskBand.LOW: 0,
    RiskBand.MEDIUM: 1,
    RiskBand.HIGH: 2,
    RiskBand.CRITICAL: 3,
}

DEFAULT_POLICY_CONFIGS = {
    PolicyProfile.BALANCED: PolicyConfig(
        profile=PolicyProfile.BALANCED,
        exposure_weight=0.4,
        password_weight=0.6,
        warn_threshold=40.0,
        step_up_threshold=55.0,
        enforce_mfa_threshold=75.0,
        awareness_min_exposure_band=RiskBand.HIGH,
        step_up_min_exposure_band=RiskBand.HIGH,
        enforce_mfa_min_exposure_band=RiskBand.CRITICAL,
        require_stronger_min_password_band=RiskBand.CRITICAL,
        paired_require_stronger_password_band=RiskBand.HIGH,
        paired_require_stronger_min_exposure_band=RiskBand.HIGH,
        warn_min_password_band=RiskBand.MEDIUM,
    ),
    PolicyProfile.STRICT: PolicyConfig(
        profile=PolicyProfile.STRICT,
        exposure_weight=0.45,
        password_weight=0.55,
        warn_threshold=32.0,
        step_up_threshold=48.0,
        enforce_mfa_threshold=68.0,
        awareness_min_exposure_band=RiskBand.MEDIUM,
        step_up_min_exposure_band=RiskBand.MEDIUM,
        enforce_mfa_min_exposure_band=RiskBand.HIGH,
        require_stronger_min_password_band=RiskBand.HIGH,
        paired_require_stronger_password_band=RiskBand.MEDIUM,
        paired_require_stronger_min_exposure_band=RiskBand.HIGH,
        warn_min_password_band=RiskBand.MEDIUM,
    ),
    PolicyProfile.USABILITY: PolicyConfig(
        profile=PolicyProfile.USABILITY,
        exposure_weight=0.3,
        password_weight=0.7,
        warn_threshold=48.0,
        step_up_threshold=65.0,
        enforce_mfa_threshold=82.0,
        awareness_min_exposure_band=RiskBand.CRITICAL,
        step_up_min_exposure_band=RiskBand.CRITICAL,
        enforce_mfa_min_exposure_band=RiskBand.CRITICAL,
        require_stronger_min_password_band=RiskBand.CRITICAL,
        paired_require_stronger_password_band=RiskBand.HIGH,
        paired_require_stronger_min_exposure_band=RiskBand.CRITICAL,
        warn_min_password_band=RiskBand.HIGH,
    ),
}


def _append_unique(actions: list[HardeningAction], action: HardeningAction) -> None:
    """Add an action once while preserving order."""
    if action not in actions:
        actions.append(action)


def _band_at_least(current: RiskBand, threshold: RiskBand) -> bool:
    """Compare two risk bands using their ordinal severity."""
    return BAND_RANK[current] >= BAND_RANK[threshold]


def get_policy_config(profile: PolicyProfile | str = PolicyProfile.BALANCED) -> PolicyConfig:
    """Return a named baseline policy configuration."""
    resolved = profile if isinstance(profile, PolicyProfile) else PolicyProfile(profile)
    return DEFAULT_POLICY_CONFIGS[resolved]


def list_policy_configs() -> list[PolicyConfig]:
    """Return all built-in policy configurations."""
    return [DEFAULT_POLICY_CONFIGS[profile] for profile in PolicyProfile]


def recommend_hardening(
    exposure: ExposureAssessment,
    password_risk: PasswordRiskAssessment,
    config: PolicyConfig | None = None,
) -> HardeningRecommendation:
    """Combine exposure and password risk into a baseline hardening recommendation."""
    if exposure.employee_id != password_risk.employee_id:
        raise ValueError("exposure and password_risk must refer to the same employee_id")
    resolved_config = config or get_policy_config()

    combined_score = round(
        (exposure.score * resolved_config.exposure_weight)
        + (password_risk.score * resolved_config.password_weight),
        2,
    )
    supporting_actions: list[HardeningAction] = []
    rationale: list[str] = []

    if _band_at_least(exposure.band, resolved_config.awareness_min_exposure_band):
        _append_unique(supporting_actions, HardeningAction.PRIORITIZE_AWARENESS_TRAINING)
    if (
        _band_at_least(exposure.band, resolved_config.enforce_mfa_min_exposure_band)
        or combined_score >= resolved_config.enforce_mfa_threshold
    ):
        _append_unique(supporting_actions, HardeningAction.ENFORCE_MFA)
    elif (
        _band_at_least(exposure.band, resolved_config.step_up_min_exposure_band)
        or combined_score >= resolved_config.step_up_threshold
    ):
        _append_unique(supporting_actions, HardeningAction.STEP_UP_AUTHENTICATION)

    if _band_at_least(password_risk.band, resolved_config.require_stronger_min_password_band):
        primary_action = HardeningAction.REQUIRE_STRONGER_PASSWORD
    elif (
        _band_at_least(password_risk.band, resolved_config.paired_require_stronger_password_band)
        and _band_at_least(exposure.band, resolved_config.paired_require_stronger_min_exposure_band)
    ):
        primary_action = HardeningAction.REQUIRE_STRONGER_PASSWORD
    elif _band_at_least(exposure.band, resolved_config.enforce_mfa_min_exposure_band):
        primary_action = HardeningAction.ENFORCE_MFA
    elif _band_at_least(exposure.band, resolved_config.step_up_min_exposure_band):
        primary_action = HardeningAction.STEP_UP_AUTHENTICATION
    elif _band_at_least(password_risk.band, resolved_config.warn_min_password_band):
        primary_action = HardeningAction.WARN
    elif combined_score >= resolved_config.warn_threshold:
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
        policy_profile=resolved_config.profile,
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


def policy_configs_to_json(pretty: bool = False) -> str:
    """Serialize all built-in policy profiles as JSON."""
    payload = [config.to_dict() for config in list_policy_configs()]
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
