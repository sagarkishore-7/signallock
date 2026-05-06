"""FastAPI service layer for SignalLock Audit and Interactive modes.

Requires the ``api`` optional dependency group:
    pip install signallock[api]

Stateless by design: every request body carries its own profile data;
the server stores nothing about callers, never echoes passwords back,
and only references matched-token strings inside explanations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .explanation import explain_recommendation
from .exposure import (
    profile_to_attribute_vector,
    score_exposure,
    score_profiles_exposure,
)
from .password_risk import score_password_for_profile
from .policy import (
    get_policy_config,
    list_policy_configs,
    recommend_hardening,
)
from .schemas import (
    Platform,
    PolicyProfile,
    PublicProfile,
    RoleSeniority,
)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


def _require_fastapi() -> None:
    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is required for the API service layer. "
            "Install it with: pip install signallock[api]"
        )


# Pydantic request models are defined at module level so FastAPI's
# type-introspection can resolve them for body parsing. They are only
# imported and evaluated when ``fastapi`` and ``pydantic`` are installed.
if _FASTAPI_AVAILABLE:

    class PublicProfileIn(BaseModel):
        """Wire format for a public profile, mirroring schemas.PublicProfile."""

        employee_id: str
        full_name: str
        title: str
        department: str
        organization: str
        role_seniority: str
        email_format: str
        location: str
        tenure_start_year: int
        platforms: list[str] = Field(default_factory=list)
        public_usernames: list[str] = Field(default_factory=list)
        interests: list[str] = Field(default_factory=list)
        preferred_name: str | None = None
        education: str | None = None
        bio: str | None = None

        def to_dataclass(self) -> PublicProfile:
            try:
                return PublicProfile(
                    employee_id=self.employee_id,
                    full_name=self.full_name,
                    title=self.title,
                    department=self.department,
                    organization=self.organization,
                    role_seniority=RoleSeniority(self.role_seniority),
                    email_format=self.email_format,
                    location=self.location,
                    tenure_start_year=self.tenure_start_year,
                    platforms=[Platform(p) for p in self.platforms],
                    public_usernames=list(self.public_usernames),
                    interests=list(self.interests),
                    preferred_name=self.preferred_name,
                    education=self.education,
                    bio=self.bio,
                )
            except (ValueError, KeyError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

    class ExposureBatchRequest(BaseModel):
        profiles: list[PublicProfileIn]

    class PasswordScoreRequest(BaseModel):
        profile: PublicProfileIn
        password: str

    class RecommendRequest(BaseModel):
        profile: PublicProfileIn
        password: str
        policy_profile: str = "balanced"

    class ExplainRequest(BaseModel):
        profile: PublicProfileIn
        password: str
        policy_profile: str = "balanced"

    class CompareRequest(BaseModel):
        profile: PublicProfileIn
        password: str
        policy_profile: str = "balanced"


def create_app(
    model_file: str | Path | None = None,
    cors_origins: list[str] | None = None,
) -> Any:
    """Build a FastAPI application bound to an optional trained model.

    Pass ``model_file`` to enable the ``/compare-scoring`` endpoint and the
    ``/recommend?ml=true`` query mode. Without a model file, the server
    operates in heuristic-only mode.

    Pass ``cors_origins`` to allow a browser-based dashboard to call the API
    from a different port. For development the typical value is
    ``["http://localhost:3000"]`` (the Next.js dev server).
    """
    _require_fastapi()

    fitted_model = None
    if model_file:
        from .model import load_model_artifacts

        fitted_model, _ = load_model_artifacts(model_file)

    app = FastAPI(
        title="SignalLock API",
        version="0.1.0",
        description=(
            "Stateless API for OSINT-calibrated password risk assessment "
            "and context-aware authentication hardening. Audit and Interactive modes."
        ),
    )

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        )

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _resolve_policy(name: str):
        try:
            return get_policy_config(PolicyProfile(name))
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"unknown policy profile {name!r}",
            ) from exc

    def _maybe_predict_band(profile: PublicProfile, password_assessment) -> Any:
        if fitted_model is None:
            return None
        from .model import predict_risk_band

        vector = profile_to_attribute_vector(profile)
        return predict_risk_band(fitted_model, vector, password_assessment)

    # ---------------------------------------------------------------------
    # Routes
    # ---------------------------------------------------------------------

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        """Liveness check + model availability."""
        return {
            "status": "ok",
            "version": app.version,
            "model_loaded": fitted_model is not None,
        }

    @app.get("/policies")
    def list_policies() -> list[dict[str, Any]]:
        """List available named policy profiles and their thresholds."""
        return [config.to_dict() for config in list_policy_configs()]

    @app.get("/demo/profiles")
    def demo_profiles(count: int = 10, seed: int = 1, organization: str = "ExampleCorp") -> dict[str, Any]:
        """Generate a synthetic roster for dashboard demos.

        This endpoint is intended for local research demos only — it bypasses
        the stateless contract by producing data, but the data is purely
        synthetic and never tied to real individuals.
        """
        from .synthetic_profiles import generate_synthetic_profiles

        if count < 1 or count > 200:
            raise HTTPException(status_code=422, detail="count must be in [1, 200]")
        profiles = generate_synthetic_profiles(count=count, organization=organization, seed=seed)
        return {
            "count": len(profiles),
            "organization": organization,
            "seed": seed,
            "profiles": [p.to_dict() for p in profiles],
        }

    @app.post("/score/exposure")
    def score_exposure_batch(request: ExposureBatchRequest) -> dict[str, Any]:
        """Audit-mode batch endpoint: list of profiles → list of exposure assessments."""
        profiles = [p.to_dataclass() for p in request.profiles]
        assessments = score_profiles_exposure(profiles)
        return {
            "count": len(assessments),
            "assessments": [a.to_dict() for a in assessments],
        }

    @app.post("/score/password")
    def score_password(request: PasswordScoreRequest) -> dict[str, Any]:
        """Interactive-mode endpoint: profile + password → password risk assessment."""
        profile = request.profile.to_dataclass()
        assessment = score_password_for_profile(request.password, profile)
        return assessment.to_dict()

    @app.post("/recommend")
    def recommend(request: RecommendRequest, ml: bool = False) -> dict[str, Any]:
        """Full pipeline: profile + password → hardening recommendation.

        Pass ``?ml=true`` to use the trained model's predicted band (requires
        ``--model-file`` at server startup).
        """
        if ml and fitted_model is None:
            raise HTTPException(
                status_code=503,
                detail="server was started without --model-file; ml=true is unavailable",
            )

        profile = request.profile.to_dataclass()
        config = _resolve_policy(request.policy_profile)
        exposure = score_exposure(profile)
        password_assessment = score_password_for_profile(request.password, profile)

        predicted_band = _maybe_predict_band(profile, password_assessment) if ml else None
        recommendation = recommend_hardening(
            exposure,
            password_assessment,
            config=config,
            predicted_password_band=predicted_band,
        )
        return {
            "exposure": exposure.to_dict(),
            "password_assessment": password_assessment.to_dict(),
            "recommendation": recommendation.to_dict(),
        }

    @app.post("/explain")
    def explain(request: ExplainRequest, ml: bool = False) -> dict[str, Any]:
        """Full pipeline + human-readable explanation paragraph."""
        if ml and fitted_model is None:
            raise HTTPException(
                status_code=503,
                detail="server was started without --model-file; ml=true is unavailable",
            )

        profile = request.profile.to_dataclass()
        config = _resolve_policy(request.policy_profile)
        exposure = score_exposure(profile)
        password_assessment = score_password_for_profile(request.password, profile)

        predicted_band = _maybe_predict_band(profile, password_assessment) if ml else None
        recommendation = recommend_hardening(
            exposure,
            password_assessment,
            config=config,
            predicted_password_band=predicted_band,
        )
        explanation = explain_recommendation(
            recommendation, profile, exposure, password_assessment
        )
        return explanation.to_dict()

    @app.post("/compare-scoring")
    def compare_scoring_endpoint(request: CompareRequest) -> dict[str, Any]:
        """Side-by-side heuristic vs ML-assisted scoring.

        Requires the server to be started with ``--model-file``.
        """
        if fitted_model is None:
            raise HTTPException(
                status_code=503,
                detail="server was started without --model-file; /compare-scoring is unavailable",
            )

        from .model import predict_risk_band
        from .schemas import ModelScoringComparison

        profile = request.profile.to_dataclass()
        config = _resolve_policy(request.policy_profile)
        exposure = score_exposure(profile)
        password_assessment = score_password_for_profile(request.password, profile)
        vector = profile_to_attribute_vector(profile)

        heuristic_rec = recommend_hardening(exposure, password_assessment, config=config)
        ml_band = predict_risk_band(fitted_model, vector, password_assessment)
        ml_rec = recommend_hardening(
            exposure,
            password_assessment,
            config=config,
            predicted_password_band=ml_band,
        )

        comparison = ModelScoringComparison(
            employee_id=profile.employee_id,
            password_length=password_assessment.password_length,
            exposure_score=exposure.score,
            exposure_band=exposure.band,
            heuristic_password_band=password_assessment.band,
            ml_predicted_band=ml_band,
            bands_agree=password_assessment.band == ml_band,
            heuristic_action=heuristic_rec.primary_action,
            ml_action=ml_rec.primary_action,
            actions_agree=heuristic_rec.primary_action == ml_rec.primary_action,
            heuristic_combined_score=heuristic_rec.combined_score,
            ml_combined_score=ml_rec.combined_score,
            heuristic_recommendation=heuristic_rec,
            ml_recommendation=ml_rec,
        )
        return comparison.to_dict()

    return app
