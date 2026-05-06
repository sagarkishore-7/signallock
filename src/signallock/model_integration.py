"""Helpers for running heuristic and ML-assisted scoring side by side."""

from __future__ import annotations

import json
from pathlib import Path

from .exposure import profile_to_attribute_vector, score_exposure
from .model import load_model_artifacts, predict_risk_band
from .password_risk import score_password_for_profile
from .policy import get_policy_config, recommend_hardening
from .schemas import (
    ModelScoringComparison,
    PolicyConfig,
    PolicyProfile,
    PublicProfile,
)


def compare_scoring(
    password: str,
    profile: PublicProfile,
    model_file: str | Path,
    config: PolicyConfig | None = None,
) -> ModelScoringComparison:
    """Run heuristic and ML-assisted scoring on the same (profile, password) pair.

    Returns a side-by-side comparison showing where the two approaches agree or
    diverge on band and action — the primary table for the paper's results section.
    """
    resolved_config = config or get_policy_config()

    exposure = score_exposure(profile)
    vector = profile_to_attribute_vector(profile)
    password_risk = score_password_for_profile(password, profile)

    heuristic_rec = recommend_hardening(exposure, password_risk, config=resolved_config)

    fitted_model, _ = load_model_artifacts(model_file)
    ml_band = predict_risk_band(fitted_model, vector, password_risk)
    ml_rec = recommend_hardening(
        exposure,
        password_risk,
        config=resolved_config,
        predicted_password_band=ml_band,
    )

    return ModelScoringComparison(
        employee_id=profile.employee_id,
        password_length=password_risk.password_length,
        exposure_score=exposure.score,
        exposure_band=exposure.band,
        heuristic_password_band=password_risk.band,
        ml_predicted_band=ml_band,
        bands_agree=password_risk.band == ml_band,
        heuristic_action=heuristic_rec.primary_action,
        ml_action=ml_rec.primary_action,
        actions_agree=heuristic_rec.primary_action == ml_rec.primary_action,
        heuristic_combined_score=heuristic_rec.combined_score,
        ml_combined_score=ml_rec.combined_score,
        heuristic_recommendation=heuristic_rec,
        ml_recommendation=ml_rec,
    )


def comparison_to_json(
    comparison: ModelScoringComparison,
    pretty: bool = False,
) -> str:
    """Serialize a scoring comparison as JSON."""
    payload = comparison.to_dict()
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
