"""The demo *attacker* — targeted password guessing against the local target.

This drives :func:`eidolon.predict.mangling.generate_guesses` over a resolved
:class:`~eidolon.core.subject.Subject` (the OSINT dossier) to produce candidate
passwords in increasing-effort order, then tries each against the demo auth
service until one matches. It mirrors what a real targeted-guess attacker
(CUPP/TarGuess-style) would do with the same harvested material.

Safety boundaries (LOCALHOST ONLY):

- The attacker NEVER targets a live third-party host. Every HTTP-mode call first
  passes through :func:`assert_loopback`, which refuses any non-loopback host.
- An in-process mode (the default the offline test uses) talks to the target's
  :func:`demo.target_service.verify` seam directly, with no sockets at all.
- The attacker only ever sees the candidate *strings it generates itself*; the
  seeded password is "unknown to the attacker but seeded" into the target — it is
  only revealed by a successful match, exactly as in a real attack.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import FastAPI

from eidolon.core.subject import Subject
from eidolon.predict.mangling import generate_guesses

from .target_service import DEMO_USERNAME, verify

#: Hosts that are unambiguously the local loopback interface.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def assert_loopback(url: str) -> None:
    """Raise ``RuntimeError`` unless ``url``'s host is the local loopback.

    This is the demo's hard safety gate: the attacker is only ever permitted to
    reach a service running on this machine. Any other host (a real site, a LAN
    address, a public IP) is refused before a single request is made.
    """
    host = urlparse(url).hostname
    if host not in _LOOPBACK_HOSTS:
        raise RuntimeError(
            f"refusing non-loopback attack target {host!r}; the demo attacks "
            f"only {sorted(_LOOPBACK_HOSTS)}"
        )


def run_attack(
    *,
    subject: Subject,
    app: FastAPI | None = None,
    target_base_url: str | None = None,
    username: str = DEMO_USERNAME,
    limit: int = 5000,
    in_process: bool = True,
) -> dict[str, object]:
    """Run the targeted-guess attack and report whether the password cracked.

    The attacker generates up to ``limit`` candidates from ``subject`` and tries
    each against the target until one is accepted.

    Modes:
        * ``in_process=True`` (default): credentials are checked via
          :func:`demo.target_service.verify` against ``app`` — no network. This
          is what the offline test uses.
        * ``in_process=False``: candidates are POSTed to ``{target_base_url}/login``.
          ``target_base_url`` must be loopback (enforced by
          :func:`assert_loopback`); ``httpx`` is imported lazily.

    Args:
        subject: The resolved OSINT dossier driving guess generation.
        app: The local target app (required for in-process mode).
        target_base_url: Base URL of the running local target (HTTP mode).
        username: Account to attack.
        limit: Maximum number of candidates to try.
        in_process: Select the in-process seam (default) or HTTP transport.

    Returns:
        ``{"cracked": bool, "tries": int, "matched_category": str | None}`` —
        ``tries`` is the number of candidates attempted (the guess rank on a
        crack), and ``matched_category`` is the guess template that succeeded.
    """
    if in_process:
        if app is None:
            raise ValueError("in-process attack requires the target `app`")
        attempt = lambda pw: verify(app, username, pw)  # noqa: E731
    else:
        if target_base_url is None:
            raise ValueError("HTTP attack requires `target_base_url`")
        assert_loopback(target_base_url)
        import httpx  # lazy: HTTP mode is optional

        login_url = target_base_url.rstrip("/") + "/login"

        def attempt(pw: str) -> bool:
            resp = httpx.post(
                login_url, json={"username": username, "password": pw}
            )
            return resp.status_code == 200

    tries = 0
    for candidate in generate_guesses(subject, limit=limit):
        tries += 1
        if attempt(candidate.value):
            return {
                "cracked": True,
                "tries": tries,
                "matched_category": candidate.category,
            }

    return {"cracked": False, "tries": tries, "matched_category": None}
