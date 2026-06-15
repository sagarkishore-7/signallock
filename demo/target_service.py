"""A LOCAL, in-memory auth service used as the demo's attack target.

LOCALHOST ONLY. This service exists purely so the demo has something realistic
to authenticate against. Bind it to ``127.0.0.1`` only — it has no transport
security, no real user store, and no production hardening. Never expose it on a
routable interface.

It models a minimal login endpoint with a bcrypt-hashed password, per-username
failure counting, and lockout after ``MAX_FAILURES`` attempts. The
:func:`verify` helper allows the demo attacker to run *in process* (no sockets)
so the offline test suite needs no real network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import bcrypt
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

#: Single demo username; the whole showcase is single-account.
DEMO_USERNAME = "alice"

#: Failed-attempt budget before the account locks (models online rate-limiting).
MAX_FAILURES = 50


@dataclass
class _UserRecord:
    password_hash: bytes
    failures: int = 0
    locked: bool = False


@dataclass
class _UserStore:
    """In-memory single-process user store with rate-limit/lockout state."""

    users: dict[str, _UserRecord] = field(default_factory=dict)

    def seed(self, username: str, password: str) -> None:
        self.users[username] = _UserRecord(
            # Low cost factor: this is a localhost demo target, not a production
            # store. It keeps the attack/defense guess loop responsive.
            password_hash=bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt(rounds=6)
            )
        )

    def check(self, username: str, password: str) -> tuple[bool, bool]:
        """Return ``(ok, locked)`` for a login attempt, updating lockout state."""
        record = self.users.get(username)
        if record is None:
            return (False, False)
        if record.locked:
            return (False, True)
        if bcrypt.checkpw(password.encode("utf-8"), record.password_hash):
            record.failures = 0
            return (True, False)
        record.failures += 1
        if record.failures >= MAX_FAILURES:
            record.locked = True
        return (False, record.locked)


class LoginRequest(BaseModel):
    username: str
    password: str


def create_app(seed_password: str, *, username: str = DEMO_USERNAME) -> FastAPI:
    """Build a local FastAPI auth app seeded with one bcrypt-hashed password.

    The app exposes ``POST /login`` (200 on match, 401 otherwise, 423 when the
    account is locked) and stores the live :class:`_UserStore` on
    ``app.state.store`` so tests/the in-process attacker can reach it directly.
    """
    app = FastAPI(title="SignalLock demo target (localhost only)")
    store = _UserStore()
    store.seed(username, seed_password)
    app.state.store = store

    @app.post("/login")
    def login(req: LoginRequest) -> JSONResponse:
        ok, locked = store.check(req.username, req.password)
        if ok:
            return JSONResponse(status_code=200, content={"status": "ok"})
        if locked:
            return JSONResponse(status_code=423, content={"status": "locked"})
        return JSONResponse(status_code=401, content={"status": "unauthorized"})

    return app


def verify(app: FastAPI, username: str, password: str) -> bool:
    """In-process credential check against ``app``'s store (no HTTP).

    This is the seam the demo attacker uses for offline, socket-free simulation.
    Returns ``True`` only on a successful, non-locked-out match.
    """
    store: _UserStore = app.state.store
    ok, _locked = store.check(username, password)
    return ok
