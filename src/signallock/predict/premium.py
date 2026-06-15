"""Exposure premium — the headline metric.

    exposure_premium = baseline_guesses_log10 − contextual_guesses_log10

It quantifies, in orders of magnitude of guesses, how much *easier* a password
becomes to a personalized attacker once OSINT context is taken into account. A
large positive premium means a password that looks strong context-free is in
fact weak against an attacker who has done their homework.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .baseline import BaselineStrength
from .simulator import PredictabilityAssessment


@dataclass
class ExposurePremium:
    """Difference between context-free and context-aware guess estimates."""

    baseline_log10: float
    contextual_log10: float
    premium: float  # baseline_log10 - contextual_log10 (orders of magnitude)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def exposure_premium(
    baseline: BaselineStrength, prediction: PredictabilityAssessment
) -> ExposurePremium:
    """Compute the exposure premium for one (password, subject) pair.

    The contextual guess estimate is the simulator's guess rank when the password
    was cracked. When the password *survived* the targeted budget the personalized
    attack demonstrated no advantage, so the estimate is the larger of the budget
    ceiling and the context-free baseline — which makes the premium ~0 rather than
    spuriously large (flooring a survivor at log10(ceiling) alone made strong
    passwords score the biggest premiums, which is backwards).
    """
    if prediction.guesses_to_crack is not None:
        contextual_log10 = math.log10(max(prediction.guesses_to_crack, 1))
    else:
        # Survived the largest budget: the targeted attack did no better than the
        # context-free meter, so the contextual cost is at least the baseline (and
        # at least the ceiling). This keeps a survivor's premium at ~0.
        contextual_log10 = max(
            math.log10(max(prediction.budget_ceiling, 1)),
            baseline.guesses_log10,
        )

    return ExposurePremium(
        baseline_log10=round(baseline.guesses_log10, 4),
        contextual_log10=round(contextual_log10, 4),
        premium=round(baseline.guesses_log10 - contextual_log10, 4),
    )
