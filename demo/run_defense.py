"""The demo *defense* — show that hardening defeats the same targeted attack.

This re-runs :func:`demo.run_attack.run_attack` twice against the local target:

1. **Before** — the account holds the weak, OSINT-derived seed password, and the
   attack cracks it within budget.
2. **After** — the seed is replaced by a strong, random password (the "hardening"
   Eidolon recommends), and the identical attack now FAILS within budget.

Optionally it calls :func:`eidolon.policy.recommend` to surface the auditable
recommendation that motivated hardening — the same research-core output an
enterprise ``PolicyEnforcer`` would act on. The defense asserts the post-hardening
attack fails; a crack after hardening is a demo failure and raises.

LOCALHOST ONLY: like the attacker, this never touches a third-party host.
"""

from __future__ import annotations

import secrets

from fastapi import FastAPI

from eidolon.core.identity import ConsentedIdentity, ConsentRoster
from eidolon.core.subject import Subject
from eidolon.exposure import assess_exposure
from eidolon.policy import recommend
from eidolon.predict.simulator import simulate_predictability

from .run_attack import run_attack
from .target_service import DEMO_USERNAME


def _strong_password() -> str:
    """A high-entropy random password no targeted-guess generator will produce."""
    return secrets.token_urlsafe(24)


def _recommendation(
    subject: Subject,
    seed_password: str,
    *,
    identity: ConsentedIdentity,
    roster: ConsentRoster,
) -> dict[str, object]:
    """Run the full research pipeline to show the recommendation, if consented."""
    exposure = assess_exposure(subject)
    prediction = simulate_predictability(
        subject, seed_password, identity=identity, roster=roster
    )
    return recommend(exposure, prediction).to_dict()


def run_defense(
    *,
    app: FastAPI,
    subject: Subject,
    seed_password: str,
    username: str = DEMO_USERNAME,
    limit: int = 5000,
    identity: ConsentedIdentity | None = None,
    roster: ConsentRoster | None = None,
) -> dict[str, object]:
    """Demonstrate that hardening defeats the targeted-guess attack.

    Runs the attack against the seeded weak password, then re-seeds the target
    with a strong random password and re-runs the identical attack, asserting it
    now fails within ``limit``.

    Args:
        app: The local target app (its store is re-seeded in place).
        subject: The OSINT dossier driving the attacker.
        seed_password: The initial weak password (e.g. ``"rex2014"``).
        username: Account under test.
        limit: Guess budget for both attack runs.
        identity / roster: If both are given, the returned dict also includes the
            consent-gated ``recommendation`` that prompted hardening.

    Returns:
        ``{"before": <attack result>, "after": <attack result>, "hardened": True,
        "recommendation": <dict | None>}`` where ``after["cracked"]`` is ``False``.

    Raises:
        AssertionError: if the post-hardening attack still cracks (demo failure).
    """
    before = run_attack(
        subject=subject, app=app, username=username, limit=limit, in_process=True
    )

    recommendation = None
    if identity is not None and roster is not None:
        recommendation = _recommendation(
            subject, seed_password, identity=identity, roster=roster
        )

    # Harden: replace the weak seed with a strong random password in place.
    app.state.store.seed(username, _strong_password())

    after = run_attack(
        subject=subject, app=app, username=username, limit=limit, in_process=True
    )

    assert not after["cracked"], (
        "defense failed: targeted attack still cracked the hardened password "
        f"within {limit} guesses"
    )

    return {
        "before": before,
        "after": after,
        "hardened": True,
        "recommendation": recommendation,
    }
