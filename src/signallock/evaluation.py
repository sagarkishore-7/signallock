"""Synthetic evaluation harness for comparing policy profiles."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .exposure import score_exposure
from .password_risk import score_password_for_profile
from .policy import get_policy_config, recommend_hardening
from .schemas import (
    PolicyEvaluationRecord,
    PolicyEvaluationSummary,
    PolicyProfile,
    PublicProfile,
)


def _safe_token(value: str) -> str:
    """Convert free text into a compact alphanumeric token."""
    cleaned = "".join(char for char in value if char.isalnum())
    return cleaned or "Signal"


def generate_synthetic_password_scenarios(profile: PublicProfile) -> dict[str, str]:
    """Create defensive synthetic password scenarios for evaluation only."""
    name_seed = _safe_token(profile.preferred_name or profile.full_name.split()[0])
    year_seed = str(profile.tenure_start_year)
    org_seed = _safe_token(profile.organization.split()[0])
    interest_seed = _safe_token(profile.interests[0].split()[0]) if profile.interests else "Research"
    username_seed = _safe_token(profile.public_usernames[0]) if profile.public_usernames else "User"

    return {
        "contextual_name_year": f"{name_seed}{year_seed}!",
        "organization_year": f"{org_seed}{year_seed}!",
        "interest_year": f"{interest_seed}{year_seed}!",
        "username_suffix": f"{username_seed}!2024",
        "random_strong": "R4ndom!Quantum$Lake88",
    }


def evaluate_policy_profiles(
    profiles: list[PublicProfile],
    selected_profiles: list[PolicyProfile],
    policy_file: str | Path | None = None,
) -> tuple[list[PolicyEvaluationSummary], list[PolicyEvaluationRecord]]:
    """Evaluate one or more policy profiles over synthetic scenarios."""
    records: list[PolicyEvaluationRecord] = []
    configs = {
        policy_profile: get_policy_config(policy_profile, policy_file=policy_file)
        for policy_profile in selected_profiles
    }
    contexts = []
    total_exposure_score = 0.0
    total_password_score = 0.0
    total_password_count = 0

    for profile in profiles:
        exposure = score_exposure(profile)
        scenarios = generate_synthetic_password_scenarios(profile)
        scenario_assessments = {
            name: score_password_for_profile(password, profile)
            for name, password in scenarios.items()
        }
        contexts.append((profile, exposure, scenarios, scenario_assessments))
        total_exposure_score += exposure.score
        total_password_score += sum(
            assessment.score for assessment in scenario_assessments.values()
        )
        total_password_count += len(scenario_assessments)

        for policy_profile in selected_profiles:
            config = configs[policy_profile]
            for scenario_name, password in scenarios.items():
                password_assessment = scenario_assessments[scenario_name]
                recommendation = recommend_hardening(exposure, password_assessment, config=config)
                records.append(
                    PolicyEvaluationRecord(
                        employee_id=profile.employee_id,
                        scenario=scenario_name,
                        password=password,
                        policy_profile=policy_profile,
                        exposure_band=exposure.band,
                        password_band=password_assessment.band,
                        primary_action=recommendation.primary_action,
                        combined_score=recommendation.combined_score,
                    )
                )

    summaries: list[PolicyEvaluationSummary] = []
    average_exposure = round(total_exposure_score / len(profiles), 2)
    average_password = round(total_password_score / total_password_count, 2)

    for policy_profile in selected_profiles:
        policy_records = [record for record in records if record.policy_profile == policy_profile]
        action_counts = Counter(record.primary_action.value for record in policy_records)
        supporting_counts = Counter()
        combined_total = 0.0

        for profile, exposure, scenarios, scenario_assessments in contexts:
            config = configs[policy_profile]
            for scenario_name in scenarios:
                password_assessment = scenario_assessments[scenario_name]
                recommendation = recommend_hardening(exposure, password_assessment, config=config)
                supporting_counts.update(action.value for action in recommendation.supporting_actions)
                combined_total += recommendation.combined_score

        avg_combined = round(combined_total / len(policy_records), 2)

        summaries.append(
            PolicyEvaluationSummary(
                policy_profile=policy_profile,
                sample_count=len(profiles),
                scenario_count=len(policy_records),
                primary_action_counts=dict(sorted(action_counts.items())),
                supporting_action_counts=dict(sorted(supporting_counts.items())),
                average_combined_score=avg_combined,
                average_exposure_score=average_exposure,
                average_password_score=average_password,
            )
        )

    return summaries, records


def evaluation_results_to_json(
    summaries: list[PolicyEvaluationSummary],
    records: list[PolicyEvaluationRecord],
    include_records: bool = False,
    pretty: bool = False,
    metadata: dict[str, object] | None = None,
    comparison_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize evaluation summaries and optional records as JSON."""
    payload: dict[str, object] = {
        "summaries": [summary.to_dict() for summary in summaries],
    }
    if metadata:
        payload["metadata"] = metadata
    if comparison_table_markdown is not None:
        payload["comparison_table_markdown"] = comparison_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_records:
        payload["records"] = [record.to_dict() for record in records]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
