"""Learned predictability model: predict the simulator's budget-bucket label.

The simulator is expensive and requires the password; this model learns to
predict its risk-band label from exposure + token + generic password features,
so deployments can estimate targeted-guess risk at scale. It reports accuracy,
macro one-vs-rest AUROC, and expected calibration error (ECE), and contrasts
against the context-free zxcvbn baseline. Because labels and features come from
*different* mechanisms (simulation vs. feature engineering), accuracy is not a
foregone 1.0 — unlike the v1 prototype.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..core.enums import RiskBand
from ..core.errors import require_dependency
from .features import FEATURE_NAMES, feature_row

_BAND_VALUES = [band.value for band in (RiskBand.LOW, RiskBand.MEDIUM, RiskBand.HIGH, RiskBand.CRITICAL)]


@dataclass
class ModelEvaluation:
    """Metrics from one train/test evaluation of the predictability model."""

    train_size: int
    test_size: int
    accuracy: float
    macro_auroc: float | None
    ece: float
    baseline_accuracy: float          # zxcvbn-band accuracy on the same test set
    accuracy_delta: float             # model − baseline
    class_labels: list[str]
    feature_importances: dict[str, float] | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _expected_calibration_error(
    confidences: list[float], correct: list[bool], *, n_bins: int = 10
) -> float:
    """Standard binned ECE over the predicted-class confidence."""
    if not confidences:
        return 0.0
    total = len(confidences)
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idx = [
            i
            for i, c in enumerate(confidences)
            if (c > lo or (b == 0 and c >= lo)) and c <= hi
        ]
        if not idx:
            continue
        bin_conf = sum(confidences[i] for i in idx) / len(idx)
        bin_acc = sum(correct[i] for i in idx) / len(idx)
        ece += (len(idx) / total) * abs(bin_acc - bin_conf)
    return ece


def train_predictability_model(
    feature_dicts: list[dict[str, float]],
    labels: list[str],
    baseline_bands: list[str],
    *,
    test_size: float = 0.25,
    seed: int = 7,
):
    """Train and evaluate the predictability classifier.

    Args:
        feature_dicts: Per-sample named feature dicts.
        labels: Per-sample simulator risk-band labels (ground truth).
        baseline_bands: Per-sample zxcvbn risk bands (baseline comparison).
        test_size: Test fraction for the holdout split.
        seed: RNG seed for the split and model.

    Returns:
        ``(fitted_model, ModelEvaluation)``.

    Raises:
        DependencyError: If scikit-learn is not installed (install ``[ml]``).
        ValueError: If there are too few samples or only one class.
    """
    require_dependency("sklearn", "ml")
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import label_binarize

    if len(feature_dicts) < 8:
        raise ValueError("need at least 8 samples to train and evaluate")
    if len(set(labels)) < 2:
        raise ValueError("need at least two distinct label classes")

    X = np.array([feature_row(fd) for fd in feature_dicts], dtype=float)
    y = np.array(labels)
    base = np.array(baseline_bands)
    indices = np.arange(len(y))

    stratify = y if min(_class_counts(labels).values()) >= 2 else None
    X_tr, X_te, y_tr, y_te, _, idx_te = train_test_split(
        X, y, indices, test_size=test_size, random_state=seed, stratify=stratify
    )

    model = RandomForestClassifier(
        n_estimators=200, random_state=seed, class_weight="balanced"
    )
    model.fit(X_tr, y_tr)

    pred = model.predict(X_te)
    proba = model.predict_proba(X_te)
    accuracy = float(accuracy_score(y_te, pred))

    # Macro OvR AUROC, guarded for missing classes / degenerate splits.
    macro_auroc: float | None
    try:
        present = list(model.classes_)
        y_bin = label_binarize(y_te, classes=present)
        if y_bin.shape[1] == 1:  # binary case
            macro_auroc = float(roc_auc_score(y_te, proba[:, 1]))
        else:
            macro_auroc = float(
                roc_auc_score(y_bin, proba, average="macro", multi_class="ovr")
            )
    except (ValueError, IndexError):
        macro_auroc = None

    confidences = [float(row.max()) for row in proba]
    correct = [bool(p == t) for p, t in zip(pred, y_te)]
    ece = _expected_calibration_error(confidences, correct)

    baseline_accuracy = float(accuracy_score(y_te, base[idx_te]))

    importances = {
        name: float(weight)
        for name, weight in zip(FEATURE_NAMES, model.feature_importances_)
    }

    evaluation = ModelEvaluation(
        train_size=int(len(y_tr)),
        test_size=int(len(y_te)),
        accuracy=round(accuracy, 4),
        macro_auroc=round(macro_auroc, 4) if macro_auroc is not None else None,
        ece=round(ece, 4),
        baseline_accuracy=round(baseline_accuracy, 4),
        accuracy_delta=round(accuracy - baseline_accuracy, 4),
        class_labels=list(model.classes_),
        feature_importances=importances,
    )
    return model, evaluation


def _class_counts(labels: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return counts
