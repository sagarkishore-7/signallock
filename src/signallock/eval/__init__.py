"""Evaluation harness: dataset building, metrics, ablations, expert packets."""

from __future__ import annotations

from .dataset import (
    BuiltDataset,
    DatasetRow,
    build_dataset,
    build_dataset_from_config,
    load_observations_dir,
)
from .expert import ReviewTask, build_expert_packet, subject_summary
from .metrics import PremiumStats, ablation_study, evaluate_dataset, premium_stats

__all__ = [
    "BuiltDataset",
    "DatasetRow",
    "build_dataset",
    "build_dataset_from_config",
    "load_observations_dir",
    "ReviewTask",
    "build_expert_packet",
    "subject_summary",
    "PremiumStats",
    "ablation_study",
    "evaluate_dataset",
    "premium_stats",
]
