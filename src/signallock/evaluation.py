"""Synthetic evaluation harness for comparing policy profiles."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .exposure import score_exposure
from .password_risk import score_password_for_profile
from .policy import get_policy_config, recommend_hardening
from .schemas import (
    HardeningAction,
    PolicyCalibrationSummary,
    PolicyConfig,
    PolicyEvaluationRecord,
    PolicyEvaluationSummary,
    PolicyProfile,
    PublicProfile,
    RiskBand,
)


ACTION_SEVERITY = {
    HardeningAction.ALLOW: 0,
    HardeningAction.WARN: 1,
    HardeningAction.PRIORITIZE_AWARENESS_TRAINING: 1,
    HardeningAction.STEP_UP_AUTHENTICATION: 2,
    HardeningAction.REQUIRE_STRONGER_PASSWORD: 3,
    HardeningAction.ENFORCE_MFA: 4,
}


@dataclass(frozen=True)
class SyntheticScenarioSpec:
    """One safe synthetic scenario with proxy evaluation expectations."""

    name: str
    password: str
    expected_risk_band: RiskBand
    expected_action_floor: HardeningAction
    expected_action_ceiling: HardeningAction


def _safe_token(value: str) -> str:
    """Convert free text into a compact alphanumeric token."""
    cleaned = "".join(char for char in value if char.isalnum())
    return cleaned or "Signal"


def generate_synthetic_password_scenarios(profile: PublicProfile) -> dict[str, str]:
    """Create defensive synthetic password scenarios for evaluation only."""
    return {
        scenario.name: scenario.password
        for scenario in generate_synthetic_scenario_specs(profile)
    }


def generate_synthetic_scenario_specs(profile: PublicProfile) -> list[SyntheticScenarioSpec]:
    """Create evaluation scenarios with proxy risk expectations."""
    name_seed = _safe_token(profile.preferred_name or profile.full_name.split()[0])
    year_seed = str(profile.tenure_start_year)
    org_seed = _safe_token(profile.organization.split()[0])
    interest_seed = _safe_token(profile.interests[0].split()[0]) if profile.interests else "Research"
    username_seed = _safe_token(profile.public_usernames[0]) if profile.public_usernames else "User"
    raw_username = profile.public_usernames[0] if profile.public_usernames else "user"

    return [
        # --- original five scenarios ---
        SyntheticScenarioSpec(
            name="contextual_name_year",
            password=f"{name_seed}{year_seed}!",
            expected_risk_band=RiskBand.CRITICAL,
            expected_action_floor=HardeningAction.REQUIRE_STRONGER_PASSWORD,
            expected_action_ceiling=HardeningAction.ENFORCE_MFA,
        ),
        SyntheticScenarioSpec(
            name="organization_year",
            password=f"{org_seed}{year_seed}!",
            expected_risk_band=RiskBand.HIGH,
            expected_action_floor=HardeningAction.REQUIRE_STRONGER_PASSWORD,
            expected_action_ceiling=HardeningAction.ENFORCE_MFA,
        ),
        SyntheticScenarioSpec(
            name="interest_year",
            password=f"{interest_seed}{year_seed}!",
            expected_risk_band=RiskBand.MEDIUM,
            expected_action_floor=HardeningAction.WARN,
            expected_action_ceiling=HardeningAction.REQUIRE_STRONGER_PASSWORD,
        ),
        SyntheticScenarioSpec(
            name="username_suffix",
            password=f"{username_seed}!2024",
            expected_risk_band=RiskBand.HIGH,
            expected_action_floor=HardeningAction.REQUIRE_STRONGER_PASSWORD,
            expected_action_ceiling=HardeningAction.ENFORCE_MFA,
        ),
        SyntheticScenarioSpec(
            name="random_strong",
            password="R4ndom!Quantum$Lake88",
            expected_risk_band=RiskBand.LOW,
            expected_action_floor=HardeningAction.ALLOW,
            expected_action_ceiling=HardeningAction.WARN,
        ),
        # --- five extended scenarios for richer ML training distributions ---
        SyntheticScenarioSpec(
            name="name_only",
            # name overlap without year — no contextual_structure bonus
            password=f"{name_seed}!Xq8z",
            expected_risk_band=RiskBand.MEDIUM,
            expected_action_floor=HardeningAction.WARN,
            expected_action_ceiling=HardeningAction.REQUIRE_STRONGER_PASSWORD,
        ),
        SyntheticScenarioSpec(
            name="year_only",
            # year overlap without name — temporal signal only
            password=f"Xq8z{year_seed}!",
            expected_risk_band=RiskBand.MEDIUM,
            expected_action_floor=HardeningAction.WARN,
            expected_action_ceiling=HardeningAction.REQUIRE_STRONGER_PASSWORD,
        ),
        SyntheticScenarioSpec(
            name="generic_weak",
            # common dictionary word — generic weakness, zero contextual overlap
            password="password1!",
            expected_risk_band=RiskBand.MEDIUM,
            expected_action_floor=HardeningAction.WARN,
            expected_action_ceiling=HardeningAction.REQUIRE_STRONGER_PASSWORD,
        ),
        SyntheticScenarioSpec(
            name="interest_only",
            # interest/location word, no year — low contextual signal
            password=f"{interest_seed}Xq8z!",
            expected_risk_band=RiskBand.LOW,
            expected_action_floor=HardeningAction.ALLOW,
            expected_action_ceiling=HardeningAction.WARN,
        ),
        SyntheticScenarioSpec(
            name="username_year",
            # raw username (with punctuation) + year — identity + temporal overlap
            # threat model: HIGH because both components are public and the combination is targeted
            password=f"{raw_username}{year_seed}!",
            expected_risk_band=RiskBand.HIGH,
            expected_action_floor=HardeningAction.REQUIRE_STRONGER_PASSWORD,
            expected_action_ceiling=HardeningAction.ENFORCE_MFA,
        ),
    ]


def evaluate_policy_profiles(
    profiles: list[PublicProfile],
    selected_profiles: list[PolicyProfile],
    policy_file: str | Path | None = None,
) -> tuple[list[PolicyEvaluationSummary], list[PolicyEvaluationRecord]]:
    """Evaluate one or more policy profiles over synthetic scenarios."""
    configs = {
        policy_profile: get_policy_config(policy_profile, policy_file=policy_file)
        for policy_profile in selected_profiles
    }
    summaries: list[PolicyEvaluationSummary] = []
    records: list[PolicyEvaluationRecord] = []

    for policy_profile in selected_profiles:
        summary, policy_records, _ = evaluate_policy_config(
            profiles,
            configs[policy_profile],
        )
        summaries.append(summary)
        records.extend(policy_records)

    return summaries, records


def evaluate_policy_config(
    profiles: list[PublicProfile],
    config: PolicyConfig,
) -> tuple[PolicyEvaluationSummary, list[PolicyEvaluationRecord], PolicyCalibrationSummary]:
    """Evaluate one policy configuration over synthetic scenarios."""
    records: list[PolicyEvaluationRecord] = []
    contexts = []
    total_exposure_score = 0.0
    total_password_score = 0.0
    total_password_count = 0

    for profile in profiles:
        exposure = score_exposure(profile)
        scenario_specs = generate_synthetic_scenario_specs(profile)
        scenarios = {scenario.name: scenario.password for scenario in scenario_specs}
        scenario_spec_map = {scenario.name: scenario for scenario in scenario_specs}
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

        for scenario_name, password in scenarios.items():
            password_assessment = scenario_assessments[scenario_name]
            recommendation = recommend_hardening(exposure, password_assessment, config=config)
            scenario_spec = scenario_spec_map[scenario_name]
            severity = ACTION_SEVERITY[recommendation.primary_action]
            floor = ACTION_SEVERITY[scenario_spec.expected_action_floor]
            ceiling = ACTION_SEVERITY[scenario_spec.expected_action_ceiling]
            records.append(
                PolicyEvaluationRecord(
                    employee_id=profile.employee_id,
                    scenario=scenario_name,
                    password=password,
                    policy_profile=config.profile,
                    exposure_band=exposure.band,
                    password_band=password_assessment.band,
                    expected_risk_band=scenario_spec.expected_risk_band,
                    expected_action_floor=scenario_spec.expected_action_floor,
                    expected_action_ceiling=scenario_spec.expected_action_ceiling,
                    within_expected_range=floor <= severity <= ceiling,
                    under_hardening=severity < floor,
                    over_hardening=severity > ceiling,
                    action_severity_gap=severity - floor,
                    primary_action=recommendation.primary_action,
                    combined_score=recommendation.combined_score,
                )
            )

    action_counts = Counter(record.primary_action.value for record in records)
    supporting_counts = Counter()
    combined_total = 0.0

    for profile, exposure, scenarios, scenario_assessments in contexts:
        for scenario_name in scenarios:
            password_assessment = scenario_assessments[scenario_name]
            recommendation = recommend_hardening(exposure, password_assessment, config=config)
            supporting_counts.update(action.value for action in recommendation.supporting_actions)
            combined_total += recommendation.combined_score

    average_exposure = round(total_exposure_score / len(profiles), 2)
    average_password = round(total_password_score / total_password_count, 2)
    avg_combined = round(combined_total / len(records), 2)

    summary = PolicyEvaluationSummary(
        policy_profile=config.profile,
        sample_count=len(profiles),
        scenario_count=len(records),
        primary_action_counts=dict(sorted(action_counts.items())),
        supporting_action_counts=dict(sorted(supporting_counts.items())),
        average_combined_score=avg_combined,
        average_exposure_score=average_exposure,
        average_password_score=average_password,
    )
    calibration_summary = summarize_policy_calibration(
        records,
        selected_profiles=[config.profile],
    )[0]
    return summary, records, calibration_summary


def summarize_policy_calibration(
    records: list[PolicyEvaluationRecord],
    selected_profiles: list[PolicyProfile] | None = None,
) -> list[PolicyCalibrationSummary]:
    """Summarize proxy calibration behavior for one or more policy profiles."""
    policy_profiles = selected_profiles or sorted(
        {record.policy_profile for record in records},
        key=lambda profile: profile.value,
    )
    summaries: list[PolicyCalibrationSummary] = []

    for policy_profile in policy_profiles:
        policy_records = [record for record in records if record.policy_profile == policy_profile]
        if not policy_records:
            continue

        total_records = len(policy_records)
        high_risk_records = [
            record
            for record in policy_records
            if record.expected_risk_band in {RiskBand.HIGH, RiskBand.CRITICAL}
        ]
        low_risk_records = [
            record for record in policy_records if record.expected_risk_band == RiskBand.LOW
        ]

        summaries.append(
            PolicyCalibrationSummary(
                policy_profile=policy_profile,
                total_records=total_records,
                high_risk_record_count=len(high_risk_records),
                low_risk_record_count=len(low_risk_records),
                floor_action_match_rate=round(
                    sum(
                        1
                        for record in policy_records
                        if record.primary_action == record.expected_action_floor
                    )
                    / total_records,
                    2,
                ),
                within_expected_range_rate=round(
                    sum(1 for record in policy_records if record.within_expected_range)
                    / total_records,
                    2,
                ),
                under_hardening_rate=round(
                    sum(1 for record in policy_records if record.under_hardening)
                    / total_records,
                    2,
                ),
                over_hardening_rate=round(
                    sum(1 for record in policy_records if record.over_hardening)
                    / total_records,
                    2,
                ),
                true_positive_proxy_rate=round(
                    sum(1 for record in high_risk_records if not record.under_hardening)
                    / max(len(high_risk_records), 1),
                    2,
                ),
                false_positive_proxy_rate=round(
                    sum(1 for record in low_risk_records if record.over_hardening)
                    / max(len(low_risk_records), 1),
                    2,
                ),
                warn_or_higher_rate=round(
                    sum(
                        1
                        for record in policy_records
                        if ACTION_SEVERITY[record.primary_action] >= ACTION_SEVERITY[HardeningAction.WARN]
                    )
                    / total_records,
                    2,
                ),
                step_up_or_higher_rate=round(
                    sum(
                        1
                        for record in policy_records
                        if ACTION_SEVERITY[record.primary_action]
                        >= ACTION_SEVERITY[HardeningAction.STEP_UP_AUTHENTICATION]
                    )
                    / total_records,
                    2,
                ),
                block_or_higher_rate=round(
                    sum(
                        1
                        for record in policy_records
                        if ACTION_SEVERITY[record.primary_action]
                        >= ACTION_SEVERITY[HardeningAction.REQUIRE_STRONGER_PASSWORD]
                    )
                    / total_records,
                    2,
                ),
                mean_action_severity_gap=round(
                    sum(record.action_severity_gap for record in policy_records) / total_records,
                    2,
                ),
            )
        )

    return summaries


def evaluation_results_to_json(
    summaries: list[PolicyEvaluationSummary],
    records: list[PolicyEvaluationRecord],
    calibration_summaries: list[PolicyCalibrationSummary] | None = None,
    include_records: bool = False,
    pretty: bool = False,
    metadata: dict[str, object] | None = None,
    comparison_table_markdown: str | None = None,
    calibration_table_markdown: str | None = None,
    artifacts: dict[str, object] | None = None,
) -> str:
    """Serialize evaluation summaries and optional records as JSON."""
    payload: dict[str, object] = {
        "summaries": [summary.to_dict() for summary in summaries],
    }
    if calibration_summaries is not None:
        payload["calibration_summaries"] = [
            summary.to_dict() for summary in calibration_summaries
        ]
    if metadata:
        payload["metadata"] = metadata
    if comparison_table_markdown is not None:
        payload["comparison_table_markdown"] = comparison_table_markdown
    if calibration_table_markdown is not None:
        payload["calibration_table_markdown"] = calibration_table_markdown
    if artifacts is not None:
        payload["artifacts"] = artifacts
    if include_records:
        payload["records"] = [record.to_dict() for record in records]

    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)
