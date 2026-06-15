"""Context-free password strength baseline (zxcvbn).

This is the comparison point for the whole thesis: zxcvbn estimates strength
*without* any OSINT context. The gap between this and the context-aware
simulator is the exposure premium — the measurable harm of OSINT exposure.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from ..core.enums import RiskBand
from ..core.errors import require_dependency


@dataclass
class BaselineStrength:
    """Context-free strength estimate for one password."""

    zxcvbn_score: int          # 0 (weak) .. 4 (strong)
    guesses_log10: float       # log10 estimated guesses to crack
    band: RiskBand             # risk band (inverse of strength)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["band"] = self.band.value
        return data


def _band_from_log10(guesses_log10: float) -> RiskBand:
    """Map context-free guess estimate onto a risk band (weaker -> higher risk)."""
    if guesses_log10 < 3.0:
        return RiskBand.CRITICAL
    if guesses_log10 < 6.0:
        return RiskBand.HIGH
    if guesses_log10 < 9.0:
        return RiskBand.MEDIUM
    return RiskBand.LOW


def context_free_strength(password: str) -> BaselineStrength:
    """Estimate context-free strength via zxcvbn.

    Raises:
        DependencyError: If zxcvbn is not installed (install ``[osint]``).
    """
    require_dependency("zxcvbn", "osint")
    from zxcvbn import zxcvbn

    result = zxcvbn(password)
    guesses_log10 = float(
        result.get("guesses_log10", math.log10(max(result.get("guesses", 1), 1)))
    )
    return BaselineStrength(
        zxcvbn_score=int(result.get("score", 0)),
        guesses_log10=round(guesses_log10, 4),
        band=_band_from_log10(guesses_log10),
    )
