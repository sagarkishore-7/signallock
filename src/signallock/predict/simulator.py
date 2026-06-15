"""Bounded-budget guess simulation — the ground-truth predictability labeler.

This is the *attack* in the research sense: it runs the personalized guess
generator against a consented subject's own password and records the smallest
budget bucket at which the password falls (and the guess rank). That budget maps
to a :class:`RiskBand` — the empirical label the learned model is trained to
predict, and the basis for the exposure-premium metric.

Misuse guards (verified by tests):
  * :func:`require_consent` is called first; non-roster identities are refused.
  * The returned assessment contains **no guess strings** — only the matched
    template *category*, the reached budget, and the integer guess rank.
  * Enumeration is hard-capped at the largest defined budget.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..core.enums import BUDGET_TO_BAND, Budget, RiskBand
from ..core.identity import ConsentedIdentity, ConsentRoster, require_consent
from ..core.subject import Subject
from .mangling import generate_guesses


@dataclass
class PredictabilityAssessment:
    """Result of the bounded-budget targeted-guess simulation.

    Attributes:
        subject_id: The consented subject.
        band: Risk band from the smallest budget that reached the password.
        reached_budget: The budget bucket the password fell within, or ``None``
            if it survived the largest budget.
        guesses_to_crack: 1-based guess rank at which the password matched, or
            ``None`` if not reached. A count only — never a guess string.
        matched_category: Template category that produced the match
            ("base"/"case"/"affix"/"leet"/"combo"), or ``None``.
        budget_ceiling: The largest budget enumerated (for transparency).
    """

    subject_id: str
    band: RiskBand
    reached_budget: int | None
    guesses_to_crack: int | None
    matched_category: str | None
    budget_ceiling: int

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["band"] = self.band.value
        return data


def simulate_predictability(
    subject: Subject,
    password: str,
    *,
    identity: ConsentedIdentity,
    roster: ConsentRoster,
) -> PredictabilityAssessment:
    """Run the consent-gated targeted-guess simulation for one password.

    Args:
        subject: The resolved dossier (the attacker's harvested material).
        password: The consented owner's own password (never stored or emitted).
        identity: The consented identity (gated against ``roster``).
        roster: The active consent roster.

    Returns:
        A :class:`PredictabilityAssessment` with the reached budget, guess rank,
        matched template category, and risk band.
    """
    # Consent to *assess* is implied by roster membership; the per-source
    # allowlist governs collectors, not scoring, so no source is passed here.
    require_consent(identity, roster)

    budgets = Budget.ordered()
    ceiling = int(budgets[-1])

    reached_budget: int | None = None
    rank: int | None = None
    category: str | None = None

    for index, candidate in enumerate(
        generate_guesses(subject, limit=ceiling), start=1
    ):
        if candidate.value == password:
            rank = index
            category = candidate.category
            for budget in budgets:
                if index <= int(budget):
                    reached_budget = int(budget)
                    break
            break

    reached_key = Budget(reached_budget) if reached_budget is not None else None
    band = BUDGET_TO_BAND[reached_key]

    return PredictabilityAssessment(
        subject_id=subject.subject_id,
        band=band,
        reached_budget=reached_budget,
        guesses_to_crack=rank,
        matched_category=category,
        budget_ceiling=ceiling,
    )
