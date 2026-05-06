"""Scikit-learn classifier for targeted password risk prediction.

Requires the ``ml`` optional dependency group:
    pip install signallock[ml]
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

from .analysis import _create_unique_run_directory
from .reporting import normalize_artifact_path
from .schemas import (
    AttributeVector,
    ModelArtifacts,
    ModelCVResult,
    ModelTrainingResult,
    PasswordRiskAssessment,
    RiskBand,
    RoleSeniority,
)

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


DEFAULT_MODEL_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "models"

FEATURE_COLUMNS = [
    "seniority_rank",
    "platform_count",
    "name_token_count",
    "organization_token_count",
    "temporal_token_count",
    "identity_token_count",
    "context_token_count",
    "password_length",
    "generic_short_length",
    "generic_low_diversity",
    "generic_simple_sequence",
    "generic_repetition_pattern",
    "contextual_name_overlap",
    "contextual_org_overlap",
    "contextual_temporal_overlap",
    "contextual_identity_overlap",
    "contextual_context_overlap",
    "contextual_structure",
]

LABEL_COLUMN = "expected_risk_band"
HEURISTIC_COLUMN = "password_band"

_SENIORITY_RANK = {
    RoleSeniority.INDIVIDUAL_CONTRIBUTOR: 0,
    RoleSeniority.MANAGER: 1,
    RoleSeniority.DIRECTOR: 2,
    RoleSeniority.VP: 3,
    RoleSeniority.C_SUITE: 4,
}


def _require_sklearn() -> None:
    if not _SKLEARN_AVAILABLE:
        raise ImportError(
            "scikit-learn is required for model training and inference. "
            "Install it with: pip install signallock[ml]"
        )


def extract_features(
    vector: AttributeVector,
    password_risk: PasswordRiskAssessment,
) -> dict[str, float]:
    """Build a feature dict from an AttributeVector and PasswordRiskAssessment."""
    return {
        "seniority_rank": float(_SENIORITY_RANK[vector.role_seniority]),
        "platform_count": float(vector.platform_count),
        "name_token_count": float(len(vector.name_tokens)),
        "organization_token_count": float(len(vector.organization_tokens)),
        "temporal_token_count": float(len(vector.temporal_tokens)),
        "identity_token_count": float(len(vector.identity_tokens)),
        "context_token_count": float(len(vector.context_tokens)),
        "password_length": float(password_risk.password_length),
        "generic_short_length": password_risk.generic_signals["short_length"],
        "generic_low_diversity": password_risk.generic_signals["low_diversity"],
        "generic_simple_sequence": password_risk.generic_signals["simple_sequence"],
        "generic_repetition_pattern": password_risk.generic_signals["repetition_pattern"],
        "contextual_name_overlap": password_risk.contextual_signals["name_overlap"],
        "contextual_org_overlap": password_risk.contextual_signals["organization_overlap"],
        "contextual_temporal_overlap": password_risk.contextual_signals["temporal_overlap"],
        "contextual_identity_overlap": password_risk.contextual_signals["identity_overlap"],
        "contextual_context_overlap": password_risk.contextual_signals["context_overlap"],
        "contextual_structure": password_risk.contextual_signals["contextual_structure"],
    }


def train_model(
    records: list[object],
    model_type: str = "gradient_boosting",
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[ModelTrainingResult, object]:
    """Train a risk-band classifier on DatasetRecord instances.

    Returns the training result metadata and the fitted sklearn estimator.
    Requires scikit-learn (``pip install signallock[ml]``).
    """
    _require_sklearn()

    X = [[float(getattr(r, col)) for col in FEATURE_COLUMNS] for r in records]
    y_label = [getattr(r, LABEL_COLUMN).value for r in records]
    y_heuristic = [getattr(r, HEURISTIC_COLUMN).value for r in records]

    X_train, X_test, y_train, y_test, _, y_heuristic_test = train_test_split(
        X,
        y_label,
        y_heuristic,
        test_size=test_size,
        random_state=random_state,
        stratify=y_label,
    )

    clf = _build_estimator(model_type, random_state)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    model_accuracy = round(float(accuracy_score(y_test, y_pred)), 4)
    heuristic_accuracy = round(float(accuracy_score(y_test, y_heuristic_test)), 4)
    accuracy_delta = round(model_accuracy - heuristic_accuracy, 4)

    report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    class_report = {k: v for k, v in report_dict.items() if k != "accuracy"}

    feature_importances: dict[str, float] | None = None
    coefficients: dict[str, list[float]] | None = None
    if hasattr(clf, "feature_importances_"):
        feature_importances = {
            col: round(float(imp), 6)
            for col, imp in zip(FEATURE_COLUMNS, clf.feature_importances_)
        }
    if hasattr(clf, "coef_"):
        coefficients = {
            label: [round(float(v), 6) for v in coef]
            for label, coef in zip(clf.classes_, clf.coef_)
        }

    result = ModelTrainingResult(
        model_type=model_type,
        feature_names=list(FEATURE_COLUMNS),
        class_labels=list(clf.classes_),
        train_size=len(X_train),
        test_size=len(X_test),
        test_accuracy=model_accuracy,
        heuristic_test_accuracy=heuristic_accuracy,
        accuracy_delta=accuracy_delta,
        class_report=class_report,
        feature_importances=feature_importances,
        coefficients=coefficients,
    )
    return result, clf


def train_model_cv(
    records: list[object],
    n_folds: int = 5,
    model_type: str = "gradient_boosting",
    random_state: int = 42,
) -> ModelCVResult:
    """Evaluate a risk-band classifier with stratified k-fold cross-validation.

    Reports mean ± std accuracy for both the model and the heuristic baseline on
    the same test folds — the paper's Table 1 metric with confidence bounds.
    Requires scikit-learn (``pip install signallock[ml]``).
    """
    _require_sklearn()
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import accuracy_score as _acc

    X = [[float(getattr(r, col)) for col in FEATURE_COLUMNS] for r in records]
    y_label = [getattr(r, LABEL_COLUMN).value for r in records]
    y_heuristic = [getattr(r, HEURISTIC_COLUMN).value for r in records]

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    model_accs: list[float] = []
    heuristic_accs: list[float] = []
    fold_results: list[dict[str, object]] = []
    class_labels: list[str] = []

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(X, y_label)):
        X_train = [X[i] for i in train_idx]
        X_test = [X[i] for i in test_idx]
        y_train = [y_label[i] for i in train_idx]
        y_test = [y_label[i] for i in test_idx]
        y_heur_test = [y_heuristic[i] for i in test_idx]

        clf = _build_estimator(model_type, random_state + fold_idx)
        clf.fit(X_train, y_train)

        if not class_labels:
            class_labels = list(clf.classes_)

        y_pred = clf.predict(X_test)
        model_acc = round(float(_acc(y_test, y_pred)), 4)
        heur_acc = round(float(_acc(y_test, y_heur_test)), 4)

        model_accs.append(model_acc)
        heuristic_accs.append(heur_acc)
        fold_results.append(
            {
                "fold": fold_idx + 1,
                "train_size": len(X_train),
                "test_size": len(X_test),
                "model_accuracy": model_acc,
                "heuristic_accuracy": heur_acc,
                "accuracy_delta": round(model_acc - heur_acc, 4),
            }
        )

    return ModelCVResult(
        model_type=model_type,
        n_folds=n_folds,
        feature_names=list(FEATURE_COLUMNS),
        class_labels=class_labels,
        record_count=len(records),
        model_accuracy_mean=round(sum(model_accs) / n_folds, 4),
        model_accuracy_std=round(_std(model_accs), 4),
        heuristic_accuracy_mean=round(sum(heuristic_accs) / n_folds, 4),
        heuristic_accuracy_std=round(_std(heuristic_accs), 4),
        accuracy_delta_mean=round(
            sum(model_accs) / n_folds - sum(heuristic_accs) / n_folds, 4
        ),
        fold_results=fold_results,
    )


def predict_risk_band(
    fitted_model: object,
    vector: AttributeVector,
    password_risk: PasswordRiskAssessment,
) -> RiskBand:
    """Predict the targeted risk band for one (profile, password) pair.

    Requires scikit-learn (``pip install signallock[ml]``).
    """
    _require_sklearn()
    features = extract_features(vector, password_risk)
    X = [[features[col] for col in FEATURE_COLUMNS]]
    prediction = fitted_model.predict(X)[0]
    return RiskBand(prediction)


def save_model(
    fitted_model: object,
    result: ModelTrainingResult,
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> ModelArtifacts:
    """Persist a trained model and its metadata to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_MODEL_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    model_path = run_dir / f"model_{result.model_type}.pkl"
    metadata_path = run_dir / "model_metadata.json"

    with open(model_path, "wb") as fh:
        pickle.dump(fitted_model, fh)

    metadata = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "result": result.to_dict(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return ModelArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        model_file=str(model_path.resolve()),
        metadata_file=str(metadata_path.resolve()),
        model_type=result.model_type,
    )


def load_model_artifacts(model_file: str | Path) -> tuple[object, ModelTrainingResult]:
    """Load a saved model and its training metadata from disk."""
    model_path = Path(model_file)
    metadata_path = model_path.parent / "model_metadata.json"

    with open(model_path, "rb") as fh:
        fitted_model = pickle.load(fh)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    result = _result_from_dict(metadata["result"])
    return fitted_model, result


def training_results_to_json(
    result: ModelTrainingResult,
    pretty: bool = False,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize training results as JSON."""
    payload: dict[str, object] = {"result": result.to_dict()}
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _build_estimator(model_type: str, random_state: int) -> object:
    if model_type == "logistic":
        return LogisticRegression(max_iter=1000, random_state=random_state)
    if model_type == "gradient_boosting":
        return GradientBoostingClassifier(n_estimators=100, random_state=random_state)
    raise ValueError(
        f"unknown model_type {model_type!r} — choose 'logistic' or 'gradient_boosting'"
    )


def _std(values: list[float]) -> float:
    """Population standard deviation of a list of floats."""
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return round(variance ** 0.5, 4)


def _result_from_dict(data: dict[str, object]) -> ModelTrainingResult:
    return ModelTrainingResult(
        model_type=str(data["model_type"]),
        feature_names=list(data["feature_names"]),
        class_labels=list(data["class_labels"]),
        train_size=int(data["train_size"]),
        test_size=int(data["test_size"]),
        test_accuracy=float(data["test_accuracy"]),
        heuristic_test_accuracy=float(data["heuristic_test_accuracy"]),
        accuracy_delta=float(data["accuracy_delta"]),
        class_report=dict(data["class_report"]),
        feature_importances=data.get("feature_importances"),
        coefficients=data.get("coefficients"),
    )
