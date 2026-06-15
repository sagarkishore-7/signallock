"""Policy engine: combine exposure and predictability into hardening actions.

Preserves the v1 combiner concept — a transparent rule layer over the two
scores — re-homed onto the new exposure/predictability assessments. The output
is an auditable recommendation: a primary action, supporting actions, and a
plain-language rationale.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..core.enums import HardeningAction, RiskBand
from ..exposure.model import ExposureAssessment
from ..predict.simulator import PredictabilityAssessment

#: A representative 0..100 score per band, used to blend predictability (which
#: is reported as a band) with the continuous exposure score.
_BAND_SCORE: dict[RiskBand, float] = {
    RiskBand.LOW: 10.0,
    RiskBand.MEDIUM: 40.0,
    RiskBand.HIGH: 70.0,
    RiskBand.CRITICAL: 95.0,
}


@dataclass
class HardeningRecommendation:
    """Policy recommendation derived from exposure and predictability."""

    subject_id: str
    exposure_score: float
    exposure_band: RiskBand
    predictability_band: RiskBand
    combined_score: float
    primary_action: HardeningAction
    supporting_actions: list[HardeningAction] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["exposure_band"] = self.exposure_band.value
        data["predictability_band"] = self.predictability_band.value
        data["primary_action"] = self.primary_action.value
        data["supporting_actions"] = [a.value for a in self.supporting_actions]
        return data


def recommend(
    exposure: ExposureAssessment,
    prediction: PredictabilityAssessment,
    *,
    exposure_weight: float = 0.5,
) -> HardeningRecommendation:
    """Combine the two assessments into an auditable hardening recommendation."""
    pred_band = prediction.band
    combined = (
        exposure_weight * exposure.score
        + (1.0 - exposure_weight) * _BAND_SCORE[pred_band]
    )

    supporting: list[HardeningAction] = []
    rationale: list[str] = []

    # Primary action is driven by how guessable the password is in context.
    if pred_band is RiskBand.CRITICAL:
        primary = HardeningAction.REQUIRE_STRONGER_PASSWORD
        supporting.append(HardeningAction.ENFORCE_MFA)
        rationale.append(
            "Password is reachable within a small targeted-guess budget given "
            "exposed OSINT material."
        )
    elif pred_band is RiskBand.HIGH:
        primary = HardeningAction.REQUIRE_STRONGER_PASSWORD
        rationale.append(
            "Password is guessable within a moderate targeted-guess budget."
        )
    elif pred_band is RiskBand.MEDIUM:
        primary = HardeningAction.WARN
        rationale.append("Password shows context-linked weaknesses.")
    else:
        primary = HardeningAction.ALLOW
        rationale.append("Password resists the bounded targeted-guess simulation.")

    # Exposure escalates supporting controls regardless of password strength.
    if exposure.band in (RiskBand.HIGH, RiskBand.CRITICAL):
        if HardeningAction.ENFORCE_MFA not in supporting and primary is not HardeningAction.ENFORCE_MFA:
            supporting.append(HardeningAction.ENFORCE_MFA)
        supporting.append(HardeningAction.STEP_UP_AUTHENTICATION)
        rationale.append(
            f"High attack surface (exposure {exposure.band.value}); "
            "amplified by cross-platform linkability."
        )
    elif exposure.band is RiskBand.MEDIUM:
        supporting.append(HardeningAction.PRIORITIZE_AWARENESS_TRAINING)
        rationale.append("Moderate public exposure warrants awareness training.")

    # De-duplicate supporting actions, preserving order and excluding primary.
    seen: set[HardeningAction] = {primary}
    deduped: list[HardeningAction] = []
    for action in supporting:
        if action not in seen:
            seen.add(action)
            deduped.append(action)

    return HardeningRecommendation(
        subject_id=exposure.subject_id,
        exposure_score=exposure.score,
        exposure_band=exposure.band,
        predictability_band=pred_band,
        combined_score=round(combined, 2),
        primary_action=primary,
        supporting_actions=deduped,
        rationale=rationale,
    )
