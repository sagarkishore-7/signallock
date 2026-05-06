"""Labeled feature-matrix dataset generator for ML training and calibration analysis."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from .analysis import _create_unique_run_directory
from .evaluation import ACTION_SEVERITY, generate_synthetic_scenario_specs
from .exposure import profile_to_attribute_vector, score_exposure
from .password_risk import score_password_for_profile
from .policy import get_policy_config, recommend_hardening
from .reporting import normalize_artifact_path
from .schemas import (
    DatasetArtifacts,
    DatasetOverview,
    DatasetRecord,
    PolicyProfile,
    PublicProfile,
    RoleSeniority,
)


DEFAULT_DATASET_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "datasets"
)

_SENIORITY_RANK = {
    RoleSeniority.INDIVIDUAL_CONTRIBUTOR: 0,
    RoleSeniority.MANAGER: 1,
    RoleSeniority.DIRECTOR: 2,
    RoleSeniority.VP: 3,
    RoleSeniority.C_SUITE: 4,
}

_CSV_FIELDNAMES = [
    "employee_id",
    "scenario_name",
    "policy_profile",
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
    "exposure_score",
    "password_score",
    "combined_score",
    "exposure_band",
    "password_band",
    "primary_action",
    "expected_risk_band",
    "expected_action_floor",
    "expected_action_ceiling",
    "within_expected_range",
    "action_severity",
    "expected_floor_severity",
    "expected_ceiling_severity",
    "action_severity_gap",
]


def generate_dataset(
    profiles: list[PublicProfile],
    policy_profile: PolicyProfile = PolicyProfile.BALANCED,
    organization: str = "ExampleCorp",
    seed: int | None = None,
    policy_file: str | Path | None = None,
) -> tuple[DatasetOverview, list[DatasetRecord]]:
    """Generate a labeled feature-matrix dataset from synthetic profiles."""
    config = get_policy_config(policy_profile, policy_file=policy_file)
    records: list[DatasetRecord] = []

    for profile in profiles:
        exposure = score_exposure(profile)
        vector = profile_to_attribute_vector(profile)
        seniority_rank = _SENIORITY_RANK[profile.role_seniority]
        specs = generate_synthetic_scenario_specs(profile)

        for spec in specs:
            password_risk = score_password_for_profile(spec.password, profile)
            recommendation = recommend_hardening(exposure, password_risk, config=config)

            action_sev = ACTION_SEVERITY[recommendation.primary_action]
            floor_sev = ACTION_SEVERITY[spec.expected_action_floor]
            ceiling_sev = ACTION_SEVERITY[spec.expected_action_ceiling]
            within_range = floor_sev <= action_sev <= ceiling_sev

            records.append(
                DatasetRecord(
                    employee_id=profile.employee_id,
                    scenario_name=spec.name,
                    policy_profile=policy_profile,
                    seniority_rank=seniority_rank,
                    platform_count=vector.platform_count,
                    name_token_count=len(vector.name_tokens),
                    organization_token_count=len(vector.organization_tokens),
                    temporal_token_count=len(vector.temporal_tokens),
                    identity_token_count=len(vector.identity_tokens),
                    context_token_count=len(vector.context_tokens),
                    password_length=password_risk.password_length,
                    generic_short_length=password_risk.generic_signals["short_length"],
                    generic_low_diversity=password_risk.generic_signals["low_diversity"],
                    generic_simple_sequence=password_risk.generic_signals["simple_sequence"],
                    generic_repetition_pattern=password_risk.generic_signals["repetition_pattern"],
                    contextual_name_overlap=password_risk.contextual_signals["name_overlap"],
                    contextual_org_overlap=password_risk.contextual_signals["organization_overlap"],
                    contextual_temporal_overlap=password_risk.contextual_signals["temporal_overlap"],
                    contextual_identity_overlap=password_risk.contextual_signals["identity_overlap"],
                    contextual_context_overlap=password_risk.contextual_signals["context_overlap"],
                    contextual_structure=password_risk.contextual_signals["contextual_structure"],
                    exposure_score=exposure.score,
                    password_score=password_risk.score,
                    combined_score=recommendation.combined_score,
                    exposure_band=exposure.band,
                    password_band=password_risk.band,
                    primary_action=recommendation.primary_action,
                    expected_risk_band=spec.expected_risk_band,
                    expected_action_floor=spec.expected_action_floor,
                    expected_action_ceiling=spec.expected_action_ceiling,
                    within_expected_range=within_range,
                    action_severity=action_sev,
                    expected_floor_severity=floor_sev,
                    expected_ceiling_severity=ceiling_sev,
                    action_severity_gap=action_sev - floor_sev,
                )
            )

    within_count = sum(1 for record in records if record.within_expected_range)
    within_rate = round(within_count / len(records), 4) if records else 0.0
    risk_band_dist = dict(Counter(record.expected_risk_band.value for record in records))
    action_dist = dict(Counter(record.primary_action.value for record in records))
    scenario_names = {spec.name for profile in profiles for spec in generate_synthetic_scenario_specs(profile)}

    overview = DatasetOverview(
        organization=organization,
        seed=seed,
        policy_profile=policy_profile,
        profile_count=len(profiles),
        scenario_count=len(scenario_names),
        record_count=len(records),
        within_expected_range_rate=within_rate,
        risk_band_distribution=risk_band_dist,
        action_distribution=action_dist,
    )
    return overview, records


def _csv_rows_to_records(rows: list[dict[str, str]]) -> list[DatasetRecord]:
    """Reconstruct DatasetRecord instances from CSV-parsed string rows."""
    from .schemas import HardeningAction, PolicyProfile, RiskBand

    result: list[DatasetRecord] = []
    for row in rows:
        result.append(
            DatasetRecord(
                employee_id=row["employee_id"],
                scenario_name=row["scenario_name"],
                policy_profile=PolicyProfile(row["policy_profile"]),
                seniority_rank=int(row["seniority_rank"]),
                platform_count=int(row["platform_count"]),
                name_token_count=int(row["name_token_count"]),
                organization_token_count=int(row["organization_token_count"]),
                temporal_token_count=int(row["temporal_token_count"]),
                identity_token_count=int(row["identity_token_count"]),
                context_token_count=int(row["context_token_count"]),
                password_length=int(row["password_length"]),
                generic_short_length=float(row["generic_short_length"]),
                generic_low_diversity=float(row["generic_low_diversity"]),
                generic_simple_sequence=float(row["generic_simple_sequence"]),
                generic_repetition_pattern=float(row["generic_repetition_pattern"]),
                contextual_name_overlap=float(row["contextual_name_overlap"]),
                contextual_org_overlap=float(row["contextual_org_overlap"]),
                contextual_temporal_overlap=float(row["contextual_temporal_overlap"]),
                contextual_identity_overlap=float(row["contextual_identity_overlap"]),
                contextual_context_overlap=float(row["contextual_context_overlap"]),
                contextual_structure=float(row["contextual_structure"]),
                exposure_score=float(row["exposure_score"]),
                password_score=float(row["password_score"]),
                combined_score=float(row["combined_score"]),
                exposure_band=RiskBand(row["exposure_band"]),
                password_band=RiskBand(row["password_band"]),
                primary_action=HardeningAction(row["primary_action"]),
                expected_risk_band=RiskBand(row["expected_risk_band"]),
                expected_action_floor=HardeningAction(row["expected_action_floor"]),
                expected_action_ceiling=HardeningAction(row["expected_action_ceiling"]),
                within_expected_range=row["within_expected_range"].lower() == "true",
                action_severity=int(row["action_severity"]),
                expected_floor_severity=int(row["expected_floor_severity"]),
                expected_ceiling_severity=int(row["expected_ceiling_severity"]),
                action_severity_gap=int(row["action_severity_gap"]),
            )
        )
    return result


def dataset_to_csv(records: list[DatasetRecord]) -> str:
    """Render dataset records as a flat CSV string."""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDNAMES)
    writer.writeheader()
    for record in records:
        writer.writerow(record.to_dict())
    return buffer.getvalue()


def write_dataset_artifacts(
    overview: DatasetOverview,
    records: list[DatasetRecord],
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> DatasetArtifacts:
    """Persist a timestamped labeled dataset bundle to disk."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_DATASET_OUTPUT_DIR)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, run_id)

    csv_text = dataset_to_csv(records)
    overview_payload = {
        "generated_at": generated_at.isoformat(),
        "run_id": resolved_run_id,
        "overview": overview.to_dict(),
    }

    records_path = run_dir / "dataset_records.csv"
    overview_path = run_dir / "dataset_overview.json"

    records_path.write_text(csv_text, encoding="utf-8")
    overview_path.write_text(json.dumps(overview_payload, indent=2) + "\n", encoding="utf-8")

    return DatasetArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        records_file=str(records_path.resolve()),
        overview_file=str(overview_path.resolve()),
    )


def dataset_results_to_json(
    overview: DatasetOverview,
    records: list[DatasetRecord],
    include_records: bool = False,
    pretty: bool = False,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize dataset generation results as JSON."""
    payload: dict[str, object] = {"overview": overview.to_dict()}
    if include_records:
        payload["records"] = [record.to_dict() for record in records]
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
