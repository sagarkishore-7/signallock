"""Generate paper figures from a built dataset and evaluation report.

Matplotlib is optional; importing this module does not require it. ``save_figures``
raises a clear :class:`DependencyError` if it is missing.
"""

from __future__ import annotations

from pathlib import Path

from ..core.errors import require_dependency
from .dataset import BuiltDataset


def save_figures(
    dataset: BuiltDataset, report: dict[str, object], output_dir: str | Path
) -> list[str]:
    """Write premium, label-distribution, and feature-importance figures.

    Returns the list of written file paths.
    """
    require_dependency("matplotlib", "viz")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    # 1) Exposure-premium histogram.
    premiums = [r.premium for r in dataset.rows]
    if premiums:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(premiums, bins=12, color="#b5179e", edgecolor="white")
        ax.axvline(0, color="black", linewidth=1, linestyle="--")
        ax.set_title("Exposure premium (zxcvbn − contextual, log10 guesses)")
        ax.set_xlabel("premium")
        ax.set_ylabel("count")
        path = out / "exposure_premium_hist.png"
        fig.tight_layout()
        fig.savefig(path, dpi=120)
        plt.close(fig)
        written.append(str(path))

    # 2) Label vs baseline band distribution.
    model = report.get("model", {})
    label_dist = report.get("label_distribution", {})
    baseline_dist = report.get("baseline_distribution", {})
    if isinstance(label_dist, dict) and label_dist:
        bands = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        label_vals = [label_dist.get(b, 0) for b in bands]
        base_vals = [baseline_dist.get(b, 0) for b in bands]  # type: ignore[union-attr]
        x = range(len(bands))
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar([i - 0.2 for i in x], label_vals, width=0.4, label="Eidolon (contextual)")
        ax.bar([i + 0.2 for i in x], base_vals, width=0.4, label="zxcvbn (context-free)")
        ax.set_xticks(list(x))
        ax.set_xticklabels(bands)
        ax.set_title("Risk-band distribution: contextual vs context-free")
        ax.legend()
        path = out / "band_distribution.png"
        fig.tight_layout()
        fig.savefig(path, dpi=120)
        plt.close(fig)
        written.append(str(path))

    # 3) Feature importances (if the model trained).
    importances = (
        model.get("feature_importances") if isinstance(model, dict) else None
    )
    if importances:
        top = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)[:10]
        names = [n for n, _ in top][::-1]
        vals = [v for _, v in top][::-1]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.barh(names, vals, color="#3a0ca3")
        ax.set_title("Top predictive features")
        path = out / "feature_importances.png"
        fig.tight_layout()
        fig.savefig(path, dpi=120)
        plt.close(fig)
        written.append(str(path))

    return written
