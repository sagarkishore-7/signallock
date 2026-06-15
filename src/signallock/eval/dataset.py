"""Build the labeled feature dataset by running the full pipeline.

For each consented (subject, password) pair the builder runs:
    observations -> resolve -> exposure -> simulate (LABEL) + baseline -> features

The label is the bounded-budget simulator's risk band (ground truth), and the
zxcvbn band is retained as the baseline comparison column. Passwords are the
consented owners' own; they are used only to compute labels and are never
written to the dataset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..collect.snapshot import load_snapshot
from ..core.evidence import Observation
from ..core.identity import (
    ConsentedIdentity,
    ConsentRoster,
    IdentitySeeds,
)
from ..exposure.model import assess_exposure
from ..predict.baseline import context_free_strength
from ..predict.features import FEATURE_NAMES, build_features
from ..predict.premium import exposure_premium
from ..predict.simulator import simulate_predictability
from ..resolve.entity import resolve_subject


@dataclass
class DatasetRow:
    """One labeled feature row (no password or guess strings retained)."""

    subject_id: str
    features: dict[str, float]
    label_band: str           # simulator ground-truth band
    baseline_band: str        # zxcvbn context-free band
    premium: float            # exposure premium (orders of magnitude)
    reached_budget: int | None
    guesses_to_crack: int | None
    matched_category: str | None

    def flat(self) -> dict[str, object]:
        """Flattened dict for CSV/JSON export."""
        row: dict[str, object] = {"subject_id": self.subject_id}
        for name in FEATURE_NAMES:
            row[name] = self.features.get(name, 0.0)
        row.update(
            label_band=self.label_band,
            baseline_band=self.baseline_band,
            premium=self.premium,
            reached_budget=self.reached_budget,
            guesses_to_crack=self.guesses_to_crack,
            matched_category=self.matched_category,
        )
        return row


@dataclass
class BuiltDataset:
    """A built dataset plus light provenance."""

    rows: list[DatasetRow] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.rows)

    def feature_dicts(self) -> list[dict[str, float]]:
        return [r.features for r in self.rows]

    def labels(self) -> list[str]:
        return [r.label_band for r in self.rows]

    def baseline_bands(self) -> list[str]:
        return [r.baseline_band for r in self.rows]

    def to_records(self) -> list[dict[str, object]]:
        return [r.flat() for r in self.rows]


def _identity_for(subject_id: str, roster: ConsentRoster) -> ConsentedIdentity:
    """Construct a consented identity for the gate from a roster record."""
    record = roster.get(subject_id)
    if record is None:
        raise ValueError(f"subject '{subject_id}' is not in the roster")
    return ConsentedIdentity(
        subject_id=subject_id,
        seeds=IdentitySeeds(username=subject_id),
        consent=record,
    )


def build_dataset(
    observations_by_subject: dict[str, list[Observation]],
    passwords_by_subject: dict[str, list[str]],
    roster: ConsentRoster,
) -> BuiltDataset:
    """Build a labeled dataset from per-subject observations and passwords."""
    rows: list[DatasetRow] = []
    for subject_id, observations in observations_by_subject.items():
        if subject_id not in roster:
            continue  # consent gate at the dataset level
        identity = _identity_for(subject_id, roster)
        subject = resolve_subject(subject_id, observations)
        exposure = assess_exposure(subject)
        for password in passwords_by_subject.get(subject_id, []):
            prediction = simulate_predictability(
                subject, password, identity=identity, roster=roster
            )
            baseline = context_free_strength(password)
            premium = exposure_premium(baseline, prediction)
            features = build_features(subject, exposure, password, baseline)
            rows.append(
                DatasetRow(
                    subject_id=subject_id,
                    features=features,
                    label_band=prediction.band.value,
                    baseline_band=baseline.band.value,
                    premium=premium.premium,
                    reached_budget=prediction.reached_budget,
                    guesses_to_crack=prediction.guesses_to_crack,
                    matched_category=prediction.matched_category,
                )
            )
    return BuiltDataset(rows=rows)


def load_observations_dir(snapshots_dir: str | Path) -> dict[str, list[Observation]]:
    """Load every ``*.json`` snapshot in a directory, keyed by subject_id."""
    out: dict[str, list[Observation]] = {}
    for path in sorted(Path(snapshots_dir).glob("*.json")):
        observations = load_snapshot(path)
        if observations:
            out[observations[0].subject_id] = observations
    return out


def build_dataset_from_config(
    roster_path: str | Path,
    snapshots_dir: str | Path,
    passwords_path: str | Path,
) -> BuiltDataset:
    """Build a dataset from a roster, a snapshots directory, and a passwords map."""
    roster = ConsentRoster.load(roster_path)
    observations = load_observations_dir(snapshots_dir)
    passwords = json.loads(Path(passwords_path).read_text(encoding="utf-8"))
    return build_dataset(observations, passwords, roster)
