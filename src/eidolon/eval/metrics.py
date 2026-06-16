"""Evaluation metrics: model quality, exposure premium, and ablations."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from ..core.evidence import Observation
from ..core.identity import ConsentRoster
from ..exposure.model import AXIS_WEIGHTS, assess_exposure
from ..predict.learned import train_predictability_model
from ..resolve.entity import resolve_subject
from .dataset import BuiltDataset


@dataclass
class PremiumStats:
    """Distribution of the exposure premium across the dataset."""

    count: int
    mean: float
    median: float
    maximum: float
    positive_fraction: float  # share with premium > 0 (context made it weaker)

    def to_dict(self) -> dict[str, object]:
        return {
            "count": self.count,
            "mean": round(self.mean, 4),
            "median": round(self.median, 4),
            "maximum": round(self.maximum, 4),
            "positive_fraction": round(self.positive_fraction, 4),
        }


def premium_stats(dataset: BuiltDataset) -> PremiumStats:
    values = [r.premium for r in dataset.rows]
    if not values:
        return PremiumStats(0, 0.0, 0.0, 0.0, 0.0)
    return PremiumStats(
        count=len(values),
        mean=statistics.fmean(values),
        median=statistics.median(values),
        maximum=max(values),
        positive_fraction=sum(1 for v in values if v > 0) / len(values),
    )


def _band_distribution(bands: list[str]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for band in bands:
        dist[band] = dist.get(band, 0) + 1
    return dist


def evaluate_dataset(dataset: BuiltDataset, *, seed: int = 7) -> dict[str, object]:
    """Train the learned model and assemble the headline evaluation report.

    The model label is the simulator's band; the baseline is the zxcvbn band.
    Because they come from different mechanisms, accuracy is meaningful (not 1.0).
    """
    report: dict[str, object] = {
        "sample_count": len(dataset),
        "label_distribution": _band_distribution(dataset.labels()),
        "baseline_distribution": _band_distribution(dataset.baseline_bands()),
        "premium": premium_stats(dataset).to_dict(),
    }
    try:
        _, evaluation = train_predictability_model(
            dataset.feature_dicts(),
            dataset.labels(),
            dataset.baseline_bands(),
            seed=seed,
        )
        report["model"] = evaluation.to_dict()
    except ValueError as exc:
        report["model"] = {"error": str(exc)}
    return report


def ablation_study(
    observations_by_subject: dict[str, list[Observation]],
    roster: ConsentRoster,
) -> dict[str, object]:
    """Drop each exposure axis and measure the impact on exposure scores.

    For every surface axis (and the linkability multiplier) this recomputes
    exposure with that axis disabled and reports the mean change in exposure
    score and how many subjects shift risk band — the per-axis sensitivity that
    answers "which signals drive exposure?".
    """
    subjects = [
        resolve_subject(sid, obs)
        for sid, obs in observations_by_subject.items()
        if sid in roster
    ]
    if not subjects:
        return {"subjects": 0, "axes": {}}

    full = {s.subject_id: assess_exposure(s) for s in subjects}
    axes = list(AXIS_WEIGHTS) + ["linkability"]
    results: dict[str, object] = {}
    for axis in axes:
        deltas: list[float] = []
        band_changes = 0
        for subject in subjects:
            ablated = assess_exposure(subject, disabled_axes=frozenset({axis}))
            base = full[subject.subject_id]
            deltas.append(base.score - ablated.score)
            if base.band is not ablated.band:
                band_changes += 1
        results[axis] = {
            "mean_score_delta": round(statistics.fmean(deltas), 4),
            "band_changes": band_changes,
        }
    return {"subjects": len(subjects), "axes": results}
