"""Policy engine for turning risk scores into hardening actions."""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import (
    ExposureAssessment,
    HardeningAction,
    HardeningRecommendation,
    PasswordRiskAssessment,
    PolicyConfig,
    PolicyProfile,
    RiskBand,
)

# Re-export for callers that import from policy
__all__ = [
    "recommend_hardening",
    "get_policy_config",
    "list_policy_configs",
    "load_policy_configs",
    "policy_configs_to_json",
    "recommendation_to_json",
]


BAND_RANK = {
    RiskBand.LOW: 0,
    RiskBand.MEDIUM: 1,
    RiskBand.HIGH: 2,
    RiskBand.CRITICAL: 3,
}

DEFAULT_POLICY_FILE = Path(__file__).resolve().parents[2] / "configs" / "policy_profiles.json"


def _append_unique(actions: list[HardeningAction], action: HardeningAction) -> None:
    """Add an action once while preserving order."""
    if action not in actions:
        actions.append(action)


def _band_at_least(current: RiskBand, threshold: RiskBand) -> bool:
    """Compare two risk bands using their ordinal severity."""
    return BAND_RANK[current] >= BAND_RANK[threshold]


def _load_raw_policy_payload(policy_file: str | Path | None = None) -> dict[str, object]:
    """Load the raw JSON policy payload from disk."""
    resolved = Path(policy_file) if policy_file is not None else DEFAULT_POLICY_FILE
    return json.loads(resolved.read_text())


def _policy_config_from_dict(data: dict[str, object]) -> PolicyConfig:
    """Convert one JSON policy record into a typed config object."""
    return PolicyConfig(
        profile=PolicyProfile(str(data["profile"])),
        exposure_weight=float(data["exposure_weight"]),
        password_weight=float(data["password_weight"]),
        warn_threshold=float(data["warn_threshold"]),
        step_up_threshold=float(data["step_up_threshold"]),
        enforce_mfa_threshold=float(data["enforce_mfa_threshold"]),
        awareness_min_exposure_band=RiskBand(str(data["awareness_min_exposure_band"])),
        step_up_min_exposure_band=RiskBand(str(data["step_up_min_exposure_band"])),
        enforce_mfa_min_exposure_band=RiskBand(str(data["enforce_mfa_min_exposure_band"])),
        require_stronger_min_password_band=RiskBand(str(data["require_stronger_min_password_band"])),
        paired_require_stronger_password_band=RiskBand(
            str(data["paired_require_stronger_password_band"])
        ),
        paired_require_stronger_min_exposure_band=RiskBand(
            str(data["paired_require_stronger_min_exposure_band"])
        ),
        warn_min_password_band=RiskBand(str(data["warn_min_password_band"])),
    )


def load_policy_configs(
    policy_file: str | Path | None = None,
) -> dict[PolicyProfile, PolicyConfig]:
    """Load all named policy configs from disk."""
    payload = _load_raw_policy_payload(policy_file)
    profiles = payload.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("policy payload must contain a 'profiles' list")

    configs = {}
    for item in profiles:
        if not isinstance(item, dict):
            raise ValueError("each policy profile entry must be an object")
        config = _policy_config_from_dict(item)
        configs[config.profile] = config

    missing = [profile for profile in PolicyProfile if profile not in configs]
    if missing:
        raise ValueError(f"missing required policy profiles: {[profile.value for profile in missing]}")

    return configs


def get_policy_config(
    profile: PolicyProfile | str = PolicyProfile.BALANCED,
    policy_file: str | Path | None = None,
) -> PolicyConfig:
    """Return one named policy configuration."""
    resolved = profile if isinstance(profile, PolicyProfile) else PolicyProfile(profile)
    return load_policy_configs(policy_file)[resolved]


def list_policy_configs(policy_file: str | Path | None = None) -> list[PolicyConfig]:
    """Return all policy configurations from disk."""
    configs = load_policy_configs(policy_file)
    return [configs[profile] for profile in PolicyProfile]


def recommend_hardening(
    exposure: ExposureAssessment,
    password_risk: PasswordRiskAssessment,
    config: PolicyConfig | None = None,
    predicted_password_band: RiskBand | None = None,
) -> HardeningRecommendation:
    """Combine exposure and password risk into a hardening recommendation.

    When ``predicted_password_band`` is supplied (from a trained ML model), it
    replaces the heuristic ``password_risk.band`` in all band-based policy
    decisions.  The heuristic numeric score is still used for the combined score
    so the existing threshold logic remains meaningful.
    """
    if exposure.employee_id != password_risk.employee_id:
        raise ValueError("exposure and password_risk must refer to the same employee_id")
    resolved_config = config or get_policy_config()

    effective_band = predicted_password_band if predicted_password_band is not None else password_risk.band
    ml_assisted = predicted_password_band is not None

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

    if _band_at_least(effective_band, resolved_config.require_stronger_min_password_band):
        primary_action = HardeningAction.REQUIRE_STRONGER_PASSWORD
    elif (
        _band_at_least(effective_band, resolved_config.paired_require_stronger_password_band)
        and _band_at_least(exposure.band, resolved_config.paired_require_stronger_min_exposure_band)
    ):
        primary_action = HardeningAction.REQUIRE_STRONGER_PASSWORD
    elif _band_at_least(exposure.band, resolved_config.enforce_mfa_min_exposure_band):
        primary_action = HardeningAction.ENFORCE_MFA
    elif _band_at_least(exposure.band, resolved_config.step_up_min_exposure_band):
        primary_action = HardeningAction.STEP_UP_AUTHENTICATION
    elif _band_at_least(effective_band, resolved_config.warn_min_password_band):
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
        password_band=effective_band,
        combined_score=combined_score,
        policy_profile=resolved_config.profile,
        primary_action=primary_action,
        supporting_actions=supporting_actions,
        rationale=deduped_rationale[:4],
        ml_assisted=ml_assisted,
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


def policy_configs_to_json(
    pretty: bool = False,
    policy_file: str | Path | None = None,
) -> str:
    """Serialize all policy profiles as JSON."""
    payload = [config.to_dict() for config in list_policy_configs(policy_file)]
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
