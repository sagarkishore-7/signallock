"""FastAPI service for SignalLock v2.

Requires the ``api`` extra: ``pip install "signallock[api]"``.

Stateless with respect to callers: passwords arrive in request bodies, are used
only to compute scores, and are never stored or echoed back. The server loads a
consent roster and consented snapshots at startup; predictability scoring is
consent-gated like the rest of the pipeline.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .core.enums import Visibility
from .core.identity import ConsentedIdentity, ConsentRoster, IdentitySeeds
from .core.subject import Subject
from .eval.dataset import load_observations_dir
from .exposure.model import assess_exposure
from .paths import get_project_root
from .policy.engine import recommend
from .predict.baseline import context_free_strength, identity_inputs
from .predict.premium import exposure_premium
from .predict.simulator import simulate_predictability
from .resolve.entity import filter_by_visibility, resolve_subject


def _visibility(value: str | None) -> Visibility:
    """Map a ``?visibility=`` query value to the max accessibility tier."""
    return {
        "public": Visibility.PUBLIC,
        "gated": Visibility.GATED,
    }.get((value or "all").lower(), Visibility.PRIVATE)


def _default_roster_path() -> Path:
    env = os.environ.get("SIGNALLOCK_ROSTER")
    if env:
        return Path(env)
    return get_project_root() / "configs" / "osint_roster.example.json"


def _default_snapshots_dir() -> Path:
    env = os.environ.get("SIGNALLOCK_SNAPSHOTS")
    if env:
        return Path(env)
    return get_project_root() / "configs" / "snapshots"


class SubjectStore:
    """Loads the consent roster and consented snapshots, resolves subjects."""

    def __init__(self, roster_path: Path, snapshots_dir: Path) -> None:
        self.roster = (
            ConsentRoster.load(roster_path) if roster_path.exists() else ConsentRoster()
        )
        self.observations = (
            load_observations_dir(snapshots_dir) if snapshots_dir.is_dir() else {}
        )
        self._subjects: dict[tuple[str, Visibility], Subject] = {}

    def subject(
        self, subject_id: str, visibility: Visibility = Visibility.PRIVATE
    ) -> Subject:
        if subject_id not in self.roster:
            raise HTTPException(status_code=403, detail="subject not consented")
        if subject_id not in self.observations:
            raise HTTPException(status_code=404, detail="no snapshot for subject")
        key = (subject_id, visibility)
        if key not in self._subjects:
            obs = filter_by_visibility(self.observations[subject_id], visibility)
            self._subjects[key] = resolve_subject(subject_id, obs)
        return self._subjects[key]

    def identity(self, subject_id: str) -> ConsentedIdentity:
        return ConsentedIdentity(
            subject_id=subject_id,
            seeds=IdentitySeeds(username=subject_id),
            consent=self.roster.get(subject_id),  # type: ignore[arg-type]
        )


class ScoreRequest(BaseModel):
    subject_id: str = Field(..., description="A consented subject id.")


class PasswordRequest(ScoreRequest):
    password: str = Field(..., description="Owner's own password; never stored.")


def _resolve_cors_origins(cors_origins: list[str] | None) -> list[str]:
    """CORS origins from the argument, else the SIGNALLOCK_CORS_ORIGINS env var."""
    if cors_origins is not None:
        return cors_origins
    env = os.environ.get("SIGNALLOCK_CORS_ORIGINS", "")
    return [o.strip() for o in env.split(",") if o.strip()]


def create_app(
    roster_path: Path | None = None,
    snapshots_dir: Path | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Build the FastAPI app, loading roster and snapshots at startup.

    ``cors_origins`` (or the ``SIGNALLOCK_CORS_ORIGINS`` env var, comma-separated)
    enables CORS so the Next.js dashboard dev server can call the API.
    """
    store = SubjectStore(
        roster_path or _default_roster_path(),
        snapshots_dir or _default_snapshots_dir(),
    )
    app = FastAPI(title="SignalLock", version=__version__)

    origins = _resolve_cors_origins(cors_origins)
    if origins:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "subjects": len(store.roster),
        }

    @app.get("/subjects")
    def subjects(visibility: str = "all") -> list[dict[str, object]]:
        tier = _visibility(visibility)
        out: list[dict[str, object]] = []
        for subject_id in store.roster.subject_ids():
            record = store.roster.get(subject_id)
            entry: dict[str, object] = {
                "subject_id": subject_id,
                "is_dummy": bool(record.is_dummy) if record else False,
                "has_snapshot": subject_id in store.observations,
            }
            if subject_id in store.observations:
                exposure = assess_exposure(store.subject(subject_id, tier))
                entry["exposure_score"] = exposure.score
                entry["exposure_band"] = exposure.band.value
            out.append(entry)
        return out

    @app.post("/score/exposure")
    def score_exposure(req: ScoreRequest, visibility: str = "all") -> dict[str, object]:
        return assess_exposure(
            store.subject(req.subject_id, _visibility(visibility))
        ).to_dict()

    @app.post("/score/predictability")
    def score_predictability(
        req: PasswordRequest, visibility: str = "all"
    ) -> dict[str, object]:
        subject = store.subject(req.subject_id, _visibility(visibility))
        prediction = simulate_predictability(
            subject,
            req.password,
            identity=store.identity(req.subject_id),
            roster=store.roster,
        )
        return prediction.to_dict()

    @app.post("/recommend")
    def recommend_endpoint(
        req: PasswordRequest, visibility: str = "all"
    ) -> dict[str, object]:
        subject = store.subject(req.subject_id, _visibility(visibility))
        exposure = assess_exposure(subject)
        prediction = simulate_predictability(
            subject,
            req.password,
            identity=store.identity(req.subject_id),
            roster=store.roster,
        )
        return recommend(exposure, prediction).to_dict()

    @app.post("/compare-baseline")
    def compare_baseline(
        req: PasswordRequest, visibility: str = "all"
    ) -> dict[str, object]:
        subject = store.subject(req.subject_id, _visibility(visibility))
        prediction = simulate_predictability(
            subject,
            req.password,
            identity=store.identity(req.subject_id),
            roster=store.roster,
        )
        baseline = context_free_strength(
            req.password, user_inputs=identity_inputs(subject)
        )
        premium = exposure_premium(baseline, prediction)
        return {
            "subject_id": req.subject_id,
            "contextual_band": prediction.band.value,
            "baseline": baseline.to_dict(),
            "premium": premium.to_dict(),
        }

    return app


app = create_app()
