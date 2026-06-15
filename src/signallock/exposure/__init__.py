"""Exposure model: attack-surface quantification with a linkability multiplier."""

from __future__ import annotations

from .model import (
    ALPHA,
    AXIS_WEIGHTS,
    ExposureAssessment,
    assess_exposure,
    band_from_score,
)

__all__ = [
    "ALPHA",
    "AXIS_WEIGHTS",
    "ExposureAssessment",
    "assess_exposure",
    "band_from_score",
]
