"""Core schemas for the SignalLock prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class RoleSeniority(str, Enum):
    """Normalized role seniority values."""

    INDIVIDUAL_CONTRIBUTOR = "INDIVIDUAL_CONTRIBUTOR"
    MANAGER = "MANAGER"
    DIRECTOR = "DIRECTOR"
    VP = "VP"
    C_SUITE = "C_SUITE"


class Platform(str, Enum):
    """Supported public platform types."""

    LINKEDIN = "LINKEDIN"
    GITHUB = "GITHUB"
    X = "X"
    PERSONAL_WEBSITE = "PERSONAL_WEBSITE"
    SPEAKER_BIO = "SPEAKER_BIO"
    UNIVERSITY_PROFILE = "UNIVERSITY_PROFILE"
    COMPANY_DIRECTORY = "COMPANY_DIRECTORY"


class RiskBand(str, Enum):
    """Bounded risk labels used across the prototype."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HardeningAction(str, Enum):
    """Supported hardening actions for the baseline policy engine."""

    ALLOW = "ALLOW"
    WARN = "WARN"
    REQUIRE_STRONGER_PASSWORD = "REQUIRE_STRONGER_PASSWORD"
    ENFORCE_MFA = "ENFORCE_MFA"
    STEP_UP_AUTHENTICATION = "STEP_UP_AUTHENTICATION"
    PRIORITIZE_AWARENESS_TRAINING = "PRIORITIZE_AWARENESS_TRAINING"


class PolicyProfile(str, Enum):
    """Named policy profiles for baseline hardening behavior."""

    BALANCED = "balanced"
    STRICT = "strict"
    USABILITY = "usability"


def _normalize_list(values: list[str]) -> list[str]:
    """Lower noise in list fields while preserving order."""
    seen: set[str] = set()
    normalized: list[str] = []

    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)

    return normalized


def _normalize_tokens(values: list[str]) -> list[str]:
    """Normalize token lists to unique lowercase values."""
    seen: set[str] = set()
    normalized: list[str] = []

    for value in values:
        cleaned = value.strip().lower()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


@dataclass
class PublicProfile:
    """Organization-approved or synthetic public identity record."""

    employee_id: str
    full_name: str
    title: str
    department: str
    organization: str
    role_seniority: RoleSeniority
    email_format: str
    location: str
    tenure_start_year: int
    platforms: list[Platform] = field(default_factory=list)
    public_usernames: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    preferred_name: str | None = None
    education: str | None = None
    bio: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize values."""
        self.employee_id = self.employee_id.strip()
        self.full_name = self.full_name.strip()
        self.title = self.title.strip()
        self.department = self.department.strip()
        self.organization = self.organization.strip()
        self.email_format = self.email_format.strip()
        self.location = self.location.strip()
        self.preferred_name = self.preferred_name.strip() if self.preferred_name else None
        self.education = self.education.strip() if self.education else None
        self.bio = self.bio.strip() if self.bio else None
        self.public_usernames = _normalize_list(self.public_usernames)
        self.interests = _normalize_list(self.interests)

        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if not self.full_name:
            raise ValueError("full_name must be non-empty")
        if not self.title:
            raise ValueError("title must be non-empty")
        if not self.department:
            raise ValueError("department must be non-empty")
        if not self.organization:
            raise ValueError("organization must be non-empty")
        if not self.email_format:
            raise ValueError("email_format must be non-empty")
        if not self.location:
            raise ValueError("location must be non-empty")
        if not 1970 <= self.tenure_start_year <= 2100:
            raise ValueError("tenure_start_year must be between 1970 and 2100")

    @property
    def platform_count(self) -> int:
        """Return the number of public platforms."""
        return len(self.platforms)

    def to_dict(self) -> dict[str, object]:
        """Convert the profile to a JSON-serializable dictionary."""
        data = asdict(self)
        data["role_seniority"] = self.role_seniority.value
        data["platforms"] = [platform.value for platform in self.platforms]
        return data


@dataclass
class AttributeVector:
    """Normalized public attribute buckets for later feature extraction."""

    employee_id: str
    role_seniority: RoleSeniority
    name_tokens: list[str]
    organization_tokens: list[str]
    temporal_tokens: list[str]
    identity_tokens: list[str]
    context_tokens: list[str]
    platform_count: int

    def __post_init__(self) -> None:
        """Normalize token sets."""
        self.name_tokens = _normalize_tokens(self.name_tokens)
        self.organization_tokens = _normalize_tokens(self.organization_tokens)
        self.temporal_tokens = _normalize_tokens(self.temporal_tokens)
        self.identity_tokens = _normalize_tokens(self.identity_tokens)
        self.context_tokens = _normalize_tokens(self.context_tokens)

        if not self.employee_id.strip():
            raise ValueError("employee_id must be non-empty")
        if self.platform_count < 0:
            raise ValueError("platform_count must be non-negative")

    def to_dict(self) -> dict[str, object]:
        """Convert the vector to a JSON-serializable dictionary."""
        data = asdict(self)
        data["role_seniority"] = self.role_seniority.value
        return data


@dataclass
class ExposureAssessment:
    """Interpretable baseline exposure score output."""

    employee_id: str
    score: float
    band: RiskBand
    component_scores: dict[str, float]
    top_factors: list[str]

    def __post_init__(self) -> None:
        """Validate core assessment shape."""
        self.employee_id = self.employee_id.strip()
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        """Convert the assessment to a JSON-serializable dictionary."""
        data = asdict(self)
        data["band"] = self.band.value
        return data


@dataclass
class PasswordRiskAssessment:
    """Interpretable baseline password-risk score output."""

    employee_id: str
    password_length: int
    score: float
    band: RiskBand
    generic_signals: dict[str, float]
    contextual_signals: dict[str, float]
    matched_tokens: dict[str, list[str]]
    top_factors: list[str]

    def __post_init__(self) -> None:
        """Validate core assessment shape."""
        self.employee_id = self.employee_id.strip()
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if self.password_length <= 0:
            raise ValueError("password_length must be positive")
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        """Convert the assessment to a JSON-serializable dictionary."""
        data = asdict(self)
        data["band"] = self.band.value
        return data


@dataclass
class HardeningRecommendation:
    """Baseline policy recommendation derived from exposure and password risk."""

    employee_id: str
    exposure_score: float
    exposure_band: RiskBand
    password_score: float
    password_band: RiskBand
    combined_score: float
    policy_profile: PolicyProfile
    primary_action: HardeningAction
    supporting_actions: list[HardeningAction]
    rationale: list[str]
    ml_assisted: bool = False

    def __post_init__(self) -> None:
        """Validate core recommendation shape."""
        self.employee_id = self.employee_id.strip()
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if not 0.0 <= self.exposure_score <= 100.0:
            raise ValueError("exposure_score must be between 0 and 100")
        if not 0.0 <= self.password_score <= 100.0:
            raise ValueError("password_score must be between 0 and 100")
        if not 0.0 <= self.combined_score <= 100.0:
            raise ValueError("combined_score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        """Convert the recommendation to a JSON-serializable dictionary."""
        data = asdict(self)
        data["exposure_band"] = self.exposure_band.value
        data["password_band"] = self.password_band.value
        data["policy_profile"] = self.policy_profile.value
        data["primary_action"] = self.primary_action.value
        data["supporting_actions"] = [action.value for action in self.supporting_actions]
        return data


@dataclass
class ModelScoringComparison:
    """Side-by-side comparison of heuristic and ML-assisted scoring for one (profile, password) pair."""

    employee_id: str
    password_length: int
    exposure_score: float
    exposure_band: RiskBand
    heuristic_password_band: RiskBand
    ml_predicted_band: RiskBand
    bands_agree: bool
    heuristic_action: HardeningAction
    ml_action: HardeningAction
    actions_agree: bool
    heuristic_combined_score: float
    ml_combined_score: float
    heuristic_recommendation: "HardeningRecommendation"
    ml_recommendation: "HardeningRecommendation"

    def to_dict(self) -> dict[str, object]:
        """Convert the comparison to a JSON-serializable dictionary."""
        return {
            "employee_id": self.employee_id,
            "password_length": self.password_length,
            "exposure_score": self.exposure_score,
            "exposure_band": self.exposure_band.value,
            "heuristic_password_band": self.heuristic_password_band.value,
            "ml_predicted_band": self.ml_predicted_band.value,
            "bands_agree": self.bands_agree,
            "heuristic_action": self.heuristic_action.value,
            "ml_action": self.ml_action.value,
            "actions_agree": self.actions_agree,
            "heuristic_combined_score": self.heuristic_combined_score,
            "ml_combined_score": self.ml_combined_score,
            "heuristic_recommendation": self.heuristic_recommendation.to_dict(),
            "ml_recommendation": self.ml_recommendation.to_dict(),
        }


@dataclass
class PolicyConfig:
    """Configurable thresholds and weights for baseline policy decisions."""

    profile: PolicyProfile
    exposure_weight: float
    password_weight: float
    warn_threshold: float
    step_up_threshold: float
    enforce_mfa_threshold: float
    awareness_min_exposure_band: RiskBand
    step_up_min_exposure_band: RiskBand
    enforce_mfa_min_exposure_band: RiskBand
    require_stronger_min_password_band: RiskBand
    paired_require_stronger_password_band: RiskBand
    paired_require_stronger_min_exposure_band: RiskBand
    warn_min_password_band: RiskBand

    def __post_init__(self) -> None:
        """Validate core policy configuration."""
        if self.exposure_weight < 0 or self.password_weight < 0:
            raise ValueError("policy weights must be non-negative")
        weight_total = self.exposure_weight + self.password_weight
        if abs(weight_total - 1.0) > 1e-9:
            raise ValueError("policy weights must sum to 1.0")
        thresholds = (
            self.warn_threshold,
            self.step_up_threshold,
            self.enforce_mfa_threshold,
        )
        if any(threshold < 0.0 or threshold > 100.0 for threshold in thresholds):
            raise ValueError("policy thresholds must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        """Convert the config to a JSON-serializable dictionary."""
        data = asdict(self)
        data["profile"] = self.profile.value
        data["awareness_min_exposure_band"] = self.awareness_min_exposure_band.value
        data["step_up_min_exposure_band"] = self.step_up_min_exposure_band.value
        data["enforce_mfa_min_exposure_band"] = self.enforce_mfa_min_exposure_band.value
        data["require_stronger_min_password_band"] = self.require_stronger_min_password_band.value
        data["paired_require_stronger_password_band"] = (
            self.paired_require_stronger_password_band.value
        )
        data["paired_require_stronger_min_exposure_band"] = (
            self.paired_require_stronger_min_exposure_band.value
        )
        data["warn_min_password_band"] = self.warn_min_password_band.value
        return data


@dataclass
class PolicyEvaluationRecord:
    """One synthetic evaluation result for a profile-policy-scenario combination."""

    employee_id: str
    scenario: str
    password: str
    policy_profile: PolicyProfile
    exposure_band: RiskBand
    password_band: RiskBand
    expected_risk_band: RiskBand
    expected_action_floor: HardeningAction
    expected_action_ceiling: HardeningAction
    within_expected_range: bool
    under_hardening: bool
    over_hardening: bool
    action_severity_gap: int
    primary_action: HardeningAction
    combined_score: float

    def to_dict(self) -> dict[str, object]:
        """Convert the record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        data["exposure_band"] = self.exposure_band.value
        data["password_band"] = self.password_band.value
        data["expected_risk_band"] = self.expected_risk_band.value
        data["expected_action_floor"] = self.expected_action_floor.value
        data["expected_action_ceiling"] = self.expected_action_ceiling.value
        data["primary_action"] = self.primary_action.value
        return data


@dataclass
class PolicyEvaluationSummary:
    """Aggregate metrics for one policy profile over synthetic evaluation runs."""

    policy_profile: PolicyProfile
    sample_count: int
    scenario_count: int
    primary_action_counts: dict[str, int]
    supporting_action_counts: dict[str, int]
    average_combined_score: float
    average_exposure_score: float
    average_password_score: float

    def to_dict(self) -> dict[str, object]:
        """Convert the summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class PolicyCalibrationSummary:
    """Proxy calibration metrics for one policy profile over synthetic evaluation runs."""

    policy_profile: PolicyProfile
    total_records: int
    high_risk_record_count: int
    low_risk_record_count: int
    floor_action_match_rate: float
    within_expected_range_rate: float
    under_hardening_rate: float
    over_hardening_rate: float
    true_positive_proxy_rate: float
    false_positive_proxy_rate: float
    warn_or_higher_rate: float
    step_up_or_higher_rate: float
    block_or_higher_rate: float
    mean_action_severity_gap: float

    def to_dict(self) -> dict[str, object]:
        """Convert the calibration summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class EvaluationArtifacts:
    """Filesystem artifact references for a saved evaluation run."""

    run_id: str
    generated_at: str
    output_dir: str
    report_file: str
    summaries_file: str
    comparison_table_file: str
    calibration_summaries_file: str | None = None
    calibration_table_file: str | None = None
    records_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class EvaluationRunSummaryRecord:
    """Flattened view of one policy summary from one saved evaluation run."""

    run_id: str
    generated_at: str
    organization: str
    profile_count: int
    seed: int | None
    policy_profile: PolicyProfile
    sample_count: int
    scenario_count: int
    average_combined_score: float
    average_exposure_score: float
    average_password_score: float
    top_action: str
    source_report_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert the flattened record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class EvaluationRunCalibrationRecord:
    """Flattened view of one policy calibration summary from one saved evaluation run."""

    run_id: str
    generated_at: str
    organization: str
    profile_count: int
    seed: int | None
    policy_profile: PolicyProfile
    total_records: int
    high_risk_record_count: int
    low_risk_record_count: int
    within_expected_range_rate: float
    under_hardening_rate: float
    over_hardening_rate: float
    true_positive_proxy_rate: float
    false_positive_proxy_rate: float
    warn_or_higher_rate: float
    step_up_or_higher_rate: float
    block_or_higher_rate: float
    mean_action_severity_gap: float
    source_report_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert the flattened calibration record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class EvaluationRunAnalysisOverview:
    """High-level metadata for a cross-run evaluation analysis."""

    input_dir: str
    run_count: int
    row_count: int
    calibration_row_count: int
    policy_profiles: list[str]
    organizations: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the overview to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class AnalysisArtifacts:
    """Filesystem artifact references for a saved cross-run analysis."""

    run_id: str
    generated_at: str
    output_dir: str
    analysis_file: str
    comparison_table_file: str
    policy_matrix_file: str
    calibration_table_file: str | None = None
    calibration_matrix_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert analysis artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class PolicyAggregateRecord:
    """Aggregate cross-run metrics for one policy profile."""

    policy_profile: PolicyProfile
    run_count: int
    mean_combined_score: float
    mean_exposure_score: float
    mean_password_score: float
    dominant_top_action: str
    top_action_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Convert the aggregate record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class FigureArtifacts:
    """Filesystem artifact references for saved figure outputs."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    aggregate_csv_file: str
    summary_table_file: str
    score_chart_file: str
    action_chart_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert figure artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class PolicyComparisonOverview:
    """High-level metadata for a pairwise policy comparison analysis."""

    input_dir: str
    baseline_profile: PolicyProfile
    candidate_profiles: list[str]
    total_runs_scanned: int
    matched_run_count: int
    summary_count: int

    def to_dict(self) -> dict[str, object]:
        """Convert comparison overview metadata to a JSON-serializable dictionary."""
        data = asdict(self)
        data["baseline_profile"] = self.baseline_profile.value
        return data


@dataclass
class PolicyComparisonRunDelta:
    """Per-run delta between a baseline policy and a candidate policy."""

    run_id: str
    generated_at: str
    organization: str
    profile_count: int
    seed: int | None
    baseline_profile: PolicyProfile
    candidate_profile: PolicyProfile
    baseline_top_action: str
    candidate_top_action: str
    action_changed: bool
    baseline_combined_score: float
    candidate_combined_score: float
    combined_score_delta: float
    exposure_score_delta: float
    password_score_delta: float

    def to_dict(self) -> dict[str, object]:
        """Convert a per-run comparison delta to a JSON-serializable dictionary."""
        data = asdict(self)
        data["baseline_profile"] = self.baseline_profile.value
        data["candidate_profile"] = self.candidate_profile.value
        return data


@dataclass
class PolicyComparisonSummary:
    """Aggregate comparison summary for one candidate profile versus a baseline."""

    baseline_profile: PolicyProfile
    candidate_profile: PolicyProfile
    matched_run_count: int
    mean_combined_score_delta: float
    mean_exposure_score_delta: float
    mean_password_score_delta: float
    candidate_higher_combined_ratio: float
    action_change_count: int
    dominant_transition: str
    action_transition_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Convert a comparison summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["baseline_profile"] = self.baseline_profile.value
        data["candidate_profile"] = self.candidate_profile.value
        return data


@dataclass
class ComparisonArtifacts:
    """Filesystem artifact references for a saved policy comparison bundle."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    comparison_table_file: str
    run_deltas_file: str
    delta_chart_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert comparison artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ExperimentPreset:
    """Named experiment preset for repeatable evaluation workflows."""

    name: str
    description: str
    organization: str
    profile_count: int
    seeds: list[int]
    policy_profiles: list[PolicyProfile]
    baseline_profile: PolicyProfile
    comparison_candidates: list[PolicyProfile]
    include_records: bool = False

    def __post_init__(self) -> None:
        """Validate preset structure."""
        self.name = self.name.strip()
        self.description = self.description.strip()
        self.organization = self.organization.strip()
        if not self.name:
            raise ValueError("preset name must be non-empty")
        if not self.description:
            raise ValueError("preset description must be non-empty")
        if not self.organization:
            raise ValueError("organization must be non-empty")
        if self.profile_count <= 0:
            raise ValueError("profile_count must be positive")
        if not self.seeds:
            raise ValueError("seeds must be non-empty")
        if not self.policy_profiles:
            raise ValueError("policy_profiles must be non-empty")
        if self.baseline_profile not in self.policy_profiles:
            raise ValueError("baseline_profile must be included in policy_profiles")
        for candidate in self.comparison_candidates:
            if candidate not in self.policy_profiles:
                raise ValueError("comparison candidate must be included in policy_profiles")

    def to_dict(self) -> dict[str, object]:
        """Convert the preset to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "organization": self.organization,
            "profile_count": self.profile_count,
            "seeds": self.seeds,
            "policy_profiles": [profile.value for profile in self.policy_profiles],
            "baseline_profile": self.baseline_profile.value,
            "comparison_candidates": [profile.value for profile in self.comparison_candidates],
            "include_records": self.include_records,
        }


@dataclass
class PresetArtifacts:
    """Filesystem artifact references for one executed experiment preset."""

    run_id: str
    generated_at: str
    output_dir: str
    evaluations_dir: str
    analysis_dir: str
    comparisons_dir: str
    figures_dir: str
    manifest_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert preset artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class PresetExecutionSummary:
    """Summary of one executed experiment preset run."""

    preset_name: str
    description: str
    organization: str
    profile_count: int
    seeds: list[int]
    policy_profiles: list[PolicyProfile]
    baseline_profile: PolicyProfile
    comparison_candidates: list[PolicyProfile]
    include_records: bool
    generated_at: str
    evaluation_run_count: int
    evaluation_artifacts: list[dict[str, object]]
    analysis_artifacts: dict[str, object]
    comparison_artifacts: dict[str, object] | None
    figure_artifacts: dict[str, object]
    preset_artifacts: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Convert preset execution summary to a JSON-serializable dictionary."""
        return {
            "preset_name": self.preset_name,
            "description": self.description,
            "organization": self.organization,
            "profile_count": self.profile_count,
            "seeds": self.seeds,
            "policy_profiles": [profile.value for profile in self.policy_profiles],
            "baseline_profile": self.baseline_profile.value,
            "comparison_candidates": [profile.value for profile in self.comparison_candidates],
            "include_records": self.include_records,
            "generated_at": self.generated_at,
            "evaluation_run_count": self.evaluation_run_count,
            "evaluation_artifacts": self.evaluation_artifacts,
            "analysis_artifacts": self.analysis_artifacts,
            "comparison_artifacts": self.comparison_artifacts,
            "figure_artifacts": self.figure_artifacts,
            "preset_artifacts": self.preset_artifacts,
        }


@dataclass
class PresetRunRecord:
    """Flattened summary of one executed preset bundle."""

    preset_run_id: str
    preset_name: str
    description: str
    generated_at: str
    organization: str
    profile_count: int
    evaluation_run_count: int
    seed_count: int
    baseline_profile: PolicyProfile
    policy_profiles: list[str]
    comparison_candidates: list[str]
    output_dir: str
    manifest_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert the flattened preset run record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["baseline_profile"] = self.baseline_profile.value
        return data


@dataclass
class PresetPolicySummaryRecord:
    """Flattened per-policy summary extracted from one preset execution."""

    preset_run_id: str
    preset_name: str
    generated_at: str
    organization: str
    profile_count: int
    policy_profile: PolicyProfile
    is_baseline_profile: bool
    run_count: int
    mean_combined_score: float
    mean_exposure_score: float
    mean_password_score: float
    dominant_top_action: str
    source_summary_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert the preset policy summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class PresetCalibrationSummaryRecord:
    """Flattened per-policy calibration summary extracted from one preset execution."""

    preset_run_id: str
    preset_name: str
    generated_at: str
    organization: str
    profile_count: int
    policy_profile: PolicyProfile
    evaluation_run_count: int
    mean_within_expected_range_rate: float
    mean_under_hardening_rate: float
    mean_over_hardening_rate: float
    mean_true_positive_proxy_rate: float
    mean_false_positive_proxy_rate: float
    mean_step_up_or_higher_rate: float
    mean_block_or_higher_rate: float
    mean_action_severity_gap: float
    source_manifest_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert the preset calibration summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class PresetComparisonSummaryRecord:
    """Flattened per-candidate comparison summary extracted from one preset execution."""

    preset_run_id: str
    preset_name: str
    generated_at: str
    organization: str
    profile_count: int
    baseline_profile: PolicyProfile
    candidate_profile: PolicyProfile
    matched_run_count: int
    mean_combined_score_delta: float
    mean_exposure_score_delta: float
    mean_password_score_delta: float
    candidate_higher_combined_ratio: float
    action_change_count: int
    dominant_transition: str
    source_summary_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert the preset comparison summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["baseline_profile"] = self.baseline_profile.value
        data["candidate_profile"] = self.candidate_profile.value
        return data


@dataclass
class PresetResultsOverview:
    """High-level metadata for aggregated preset results."""

    input_dir: str
    preset_run_count: int
    policy_summary_count: int
    calibration_summary_count: int
    comparison_summary_count: int
    preset_names: list[str]
    organizations: list[str]
    policy_profiles: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the overview to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class PresetResultsArtifacts:
    """Filesystem artifact references for a saved preset-results summary bundle."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    preset_runs_file: str
    policy_summaries_file: str
    calibration_summaries_file: str
    comparison_summaries_file: str
    preset_table_file: str
    policy_table_file: str
    calibration_table_file: str
    comparison_table_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class PresetPolicyAggregateRecord:
    """Aggregated policy metrics within one preset family across multiple preset runs."""

    preset_name: str
    policy_profile: PolicyProfile
    preset_run_count: int
    mean_combined_score: float
    std_combined_score: float
    mean_exposure_score: float
    mean_password_score: float
    dominant_top_action: str
    baseline_run_ratio: float

    def to_dict(self) -> dict[str, object]:
        """Convert the preset policy aggregate to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class PresetCalibrationAggregateRecord:
    """Aggregated calibration metrics within one preset family across multiple preset runs."""

    preset_name: str
    policy_profile: PolicyProfile
    preset_run_count: int
    mean_within_expected_range_rate: float
    mean_under_hardening_rate: float
    mean_over_hardening_rate: float
    mean_true_positive_proxy_rate: float
    mean_false_positive_proxy_rate: float
    mean_step_up_or_higher_rate: float
    mean_block_or_higher_rate: float
    mean_action_severity_gap: float

    def to_dict(self) -> dict[str, object]:
        """Convert the preset calibration aggregate to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class PresetComparisonAggregateRecord:
    """Aggregated comparison metrics within one preset family across multiple preset runs."""

    preset_name: str
    baseline_profile: PolicyProfile
    candidate_profile: PolicyProfile
    preset_run_count: int
    mean_combined_score_delta: float
    std_combined_score_delta: float
    mean_exposure_score_delta: float
    mean_password_score_delta: float
    mean_candidate_higher_ratio: float
    mean_action_change_ratio: float
    dominant_transition: str

    def to_dict(self) -> dict[str, object]:
        """Convert the preset comparison aggregate to a JSON-serializable dictionary."""
        data = asdict(self)
        data["baseline_profile"] = self.baseline_profile.value
        data["candidate_profile"] = self.candidate_profile.value
        return data


@dataclass
class CrossPresetPolicyAggregateRecord:
    """Aggregated policy metrics across all preset families."""

    policy_profile: PolicyProfile
    preset_name_count: int
    preset_run_count: int
    mean_combined_score: float
    std_combined_score: float
    mean_exposure_score: float
    mean_password_score: float
    dominant_top_action: str

    def to_dict(self) -> dict[str, object]:
        """Convert the cross-preset policy aggregate to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class CrossPresetCalibrationAggregateRecord:
    """Aggregated calibration metrics across all preset families."""

    policy_profile: PolicyProfile
    preset_name_count: int
    preset_run_count: int
    mean_within_expected_range_rate: float
    mean_under_hardening_rate: float
    mean_over_hardening_rate: float
    mean_true_positive_proxy_rate: float
    mean_false_positive_proxy_rate: float
    mean_step_up_or_higher_rate: float
    mean_block_or_higher_rate: float
    mean_action_severity_gap: float

    def to_dict(self) -> dict[str, object]:
        """Convert the cross-preset calibration aggregate to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class CrossPresetComparisonAggregateRecord:
    """Aggregated comparison metrics across all preset families."""

    baseline_profile: PolicyProfile
    candidate_profile: PolicyProfile
    preset_name_count: int
    preset_run_count: int
    mean_combined_score_delta: float
    std_combined_score_delta: float
    mean_exposure_score_delta: float
    mean_password_score_delta: float
    mean_candidate_higher_ratio: float
    mean_action_change_ratio: float
    dominant_transition: str

    def to_dict(self) -> dict[str, object]:
        """Convert the cross-preset comparison aggregate to a JSON-serializable dictionary."""
        data = asdict(self)
        data["baseline_profile"] = self.baseline_profile.value
        data["candidate_profile"] = self.candidate_profile.value
        return data


@dataclass
class PresetAggregateOverview:
    """High-level metadata for preset aggregate analysis."""

    input_dir: str
    preset_run_count: int
    preset_policy_aggregate_count: int
    preset_calibration_aggregate_count: int
    preset_comparison_aggregate_count: int
    cross_policy_aggregate_count: int
    cross_calibration_aggregate_count: int
    cross_comparison_aggregate_count: int
    preset_names: list[str]
    policy_profiles: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the overview to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class PresetAggregateArtifacts:
    """Filesystem artifact references for saved preset aggregate bundles."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    preset_policy_csv_file: str
    preset_calibration_csv_file: str
    preset_comparison_csv_file: str
    cross_policy_csv_file: str
    cross_calibration_csv_file: str
    cross_comparison_csv_file: str
    preset_policy_table_file: str
    preset_calibration_table_file: str
    preset_comparison_table_file: str
    cross_policy_table_file: str
    cross_calibration_table_file: str
    cross_comparison_table_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ThresholdSweepRecord:
    """One threshold-sweep variant result combining score and calibration metrics."""

    variant_label: str
    base_profile: PolicyProfile
    threshold_offset: float
    warn_threshold: float
    step_up_threshold: float
    enforce_mfa_threshold: float
    sample_count: int
    scenario_count: int
    average_combined_score: float
    average_exposure_score: float
    average_password_score: float
    top_action: str
    within_expected_range_rate: float
    under_hardening_rate: float
    over_hardening_rate: float
    true_positive_proxy_rate: float
    false_positive_proxy_rate: float
    step_up_or_higher_rate: float
    block_or_higher_rate: float
    mean_action_severity_gap: float
    reference_variant_label: str = ""
    is_reference_variant: bool = False
    top_action_changed_from_reference: bool = False
    within_expected_range_delta: float = 0.0
    under_hardening_delta: float = 0.0
    over_hardening_delta: float = 0.0
    true_positive_proxy_delta: float = 0.0
    false_positive_proxy_delta: float = 0.0
    step_up_or_higher_delta: float = 0.0
    block_or_higher_delta: float = 0.0
    mean_action_severity_gap_delta: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Convert the sweep record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["base_profile"] = self.base_profile.value
        return data


@dataclass
class ThresholdSweepOverview:
    """High-level metadata for one threshold-sweep experiment."""

    base_profile: PolicyProfile
    organization: str
    profile_count: int
    seed: int | None
    threshold_offsets: list[float]
    variant_count: int
    policy_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert the overview to a JSON-serializable dictionary."""
        data = asdict(self)
        data["base_profile"] = self.base_profile.value
        return data


@dataclass
class ThresholdSweepArtifacts:
    """Filesystem artifact references for a saved threshold-sweep bundle."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    records_file: str
    table_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ThresholdSweepRunRecord:
    """One flattened record from a saved threshold-sweep bundle."""

    run_id: str
    generated_at: str
    organization: str
    profile_count: int
    seed: int | None
    base_profile: PolicyProfile
    variant_label: str
    threshold_offset: float
    warn_threshold: float
    step_up_threshold: float
    enforce_mfa_threshold: float
    sample_count: int
    scenario_count: int
    average_combined_score: float
    average_exposure_score: float
    average_password_score: float
    top_action: str
    within_expected_range_rate: float
    under_hardening_rate: float
    over_hardening_rate: float
    true_positive_proxy_rate: float
    false_positive_proxy_rate: float
    step_up_or_higher_rate: float
    block_or_higher_rate: float
    mean_action_severity_gap: float
    reference_variant_label: str
    is_reference_variant: bool
    top_action_changed_from_reference: bool
    within_expected_range_delta: float
    under_hardening_delta: float
    over_hardening_delta: float
    true_positive_proxy_delta: float
    false_positive_proxy_delta: float
    step_up_or_higher_delta: float
    block_or_higher_delta: float
    mean_action_severity_gap_delta: float
    source_summary_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert the run record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["base_profile"] = self.base_profile.value
        return data


@dataclass
class ThresholdSweepAggregateRecord:
    """Aggregate one threshold offset across multiple saved sweep runs."""

    base_profile: PolicyProfile
    threshold_offset: float
    run_count: int
    mean_warn_threshold: float
    mean_step_up_threshold: float
    mean_enforce_mfa_threshold: float
    mean_average_combined_score: float
    mean_within_expected_range_rate: float
    mean_under_hardening_rate: float
    mean_over_hardening_rate: float
    mean_true_positive_proxy_rate: float
    mean_false_positive_proxy_rate: float
    mean_step_up_or_higher_rate: float
    mean_block_or_higher_rate: float
    mean_action_severity_gap: float
    mean_within_expected_range_delta: float
    mean_false_positive_proxy_delta: float
    mean_block_or_higher_delta: float
    dominant_top_action: str
    reference_variant_ratio: float
    top_action_change_rate: float

    def to_dict(self) -> dict[str, object]:
        """Convert the aggregate record to a JSON-serializable dictionary."""
        data = asdict(self)
        data["base_profile"] = self.base_profile.value
        return data


@dataclass
class ThresholdSweepAnalysisOverview:
    """High-level metadata for one threshold-sweep analysis operation."""

    input_dir: str
    run_count: int
    row_count: int
    aggregate_count: int
    base_profiles: list[str]
    organizations: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the overview to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ThresholdSweepAnalysisArtifacts:
    """Filesystem artifact references for a saved threshold-sweep analysis bundle."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    rows_file: str
    run_table_file: str
    aggregate_file: str
    aggregate_table_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ThresholdSweepFigureArtifacts:
    """Filesystem artifact references for a saved threshold-sweep figure bundle."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    aggregate_csv_file: str
    summary_table_file: str
    within_range_chart_file: str
    false_positive_chart_file: str
    action_change_chart_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ThresholdSweepPreset:
    """Named preset for a multi-seed, multi-profile threshold-sweep experiment."""

    name: str
    description: str
    organization: str
    profile_count: int
    seeds: list[int]
    base_profiles: list[PolicyProfile]
    threshold_offsets: list[float]

    def __post_init__(self) -> None:
        """Validate preset structure."""
        self.name = self.name.strip()
        self.description = self.description.strip()
        self.organization = self.organization.strip()
        if not self.name:
            raise ValueError("preset name must be non-empty")
        if not self.description:
            raise ValueError("preset description must be non-empty")
        if not self.organization:
            raise ValueError("organization must be non-empty")
        if self.profile_count <= 0:
            raise ValueError("profile_count must be positive")
        if not self.seeds:
            raise ValueError("seeds must be non-empty")
        if not self.base_profiles:
            raise ValueError("base_profiles must be non-empty")
        if not self.threshold_offsets:
            raise ValueError("threshold_offsets must be non-empty")

    def to_dict(self) -> dict[str, object]:
        """Convert the preset to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "organization": self.organization,
            "profile_count": self.profile_count,
            "seeds": self.seeds,
            "base_profiles": [profile.value for profile in self.base_profiles],
            "threshold_offsets": self.threshold_offsets,
        }


@dataclass
class SweepPresetArtifacts:
    """Filesystem artifact references for one executed threshold-sweep preset."""

    run_id: str
    generated_at: str
    output_dir: str
    sweeps_dir: str
    analysis_dir: str
    figures_dir: str
    manifest_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert preset artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class SweepPresetExecutionSummary:
    """Summary of one executed threshold-sweep preset run."""

    preset_name: str
    description: str
    organization: str
    profile_count: int
    seeds: list[int]
    base_profiles: list[PolicyProfile]
    threshold_offsets: list[float]
    generated_at: str
    sweep_run_count: int
    sweep_artifacts: list[dict[str, object]]
    analysis_artifacts: dict[str, object]
    figure_artifacts: dict[str, object]
    preset_artifacts: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Convert sweep preset execution summary to a JSON-serializable dictionary."""
        return {
            "preset_name": self.preset_name,
            "description": self.description,
            "organization": self.organization,
            "profile_count": self.profile_count,
            "seeds": self.seeds,
            "base_profiles": [profile.value for profile in self.base_profiles],
            "threshold_offsets": self.threshold_offsets,
            "generated_at": self.generated_at,
            "sweep_run_count": self.sweep_run_count,
            "sweep_artifacts": self.sweep_artifacts,
            "analysis_artifacts": self.analysis_artifacts,
            "figure_artifacts": self.figure_artifacts,
            "preset_artifacts": self.preset_artifacts,
        }


@dataclass
class ExposureExplanation:
    """Human-readable explanation of an exposure assessment."""

    employee_id: str
    exposure_score: float
    exposure_band: RiskBand
    summary: str
    factor_sentences: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the explanation to a JSON-serializable dictionary."""
        data = asdict(self)
        data["exposure_band"] = self.exposure_band.value
        return data


@dataclass
class PasswordRiskExplanation:
    """Human-readable explanation of a password risk assessment."""

    employee_id: str
    password_score: float
    password_band: RiskBand
    summary: str
    factor_sentences: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the explanation to a JSON-serializable dictionary."""
        data = asdict(self)
        data["password_band"] = self.password_band.value
        return data


@dataclass
class HardeningExplanation:
    """Human-readable explanation of a hardening recommendation."""

    employee_id: str
    primary_action: HardeningAction
    action_sentence: str
    exposure_explanation: ExposureExplanation
    password_explanation: PasswordRiskExplanation
    full_explanation: str

    def to_dict(self) -> dict[str, object]:
        """Convert the explanation to a JSON-serializable dictionary."""
        return {
            "employee_id": self.employee_id,
            "primary_action": self.primary_action.value,
            "action_sentence": self.action_sentence,
            "exposure_explanation": self.exposure_explanation.to_dict(),
            "password_explanation": self.password_explanation.to_dict(),
            "full_explanation": self.full_explanation,
        }


@dataclass
class DatasetRecord:
    """One labeled feature row for ML training and calibration analysis."""

    # identifiers
    employee_id: str
    scenario_name: str
    policy_profile: PolicyProfile
    # profile features
    seniority_rank: int
    platform_count: int
    name_token_count: int
    organization_token_count: int
    temporal_token_count: int
    identity_token_count: int
    context_token_count: int
    # password features
    password_length: int
    generic_short_length: float
    generic_low_diversity: float
    generic_simple_sequence: float
    generic_repetition_pattern: float
    contextual_name_overlap: float
    contextual_org_overlap: float
    contextual_temporal_overlap: float
    contextual_identity_overlap: float
    contextual_context_overlap: float
    contextual_structure: float
    # scores
    exposure_score: float
    password_score: float
    combined_score: float
    # bands and actions
    exposure_band: RiskBand
    password_band: RiskBand
    primary_action: HardeningAction
    # labels
    expected_risk_band: RiskBand
    expected_action_floor: HardeningAction
    expected_action_ceiling: HardeningAction
    within_expected_range: bool
    action_severity: int
    expected_floor_severity: int
    expected_ceiling_severity: int
    action_severity_gap: int

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable and CSV-compatible dictionary."""
        return {
            "employee_id": self.employee_id,
            "scenario_name": self.scenario_name,
            "policy_profile": self.policy_profile.value,
            "seniority_rank": self.seniority_rank,
            "platform_count": self.platform_count,
            "name_token_count": self.name_token_count,
            "organization_token_count": self.organization_token_count,
            "temporal_token_count": self.temporal_token_count,
            "identity_token_count": self.identity_token_count,
            "context_token_count": self.context_token_count,
            "password_length": self.password_length,
            "generic_short_length": self.generic_short_length,
            "generic_low_diversity": self.generic_low_diversity,
            "generic_simple_sequence": self.generic_simple_sequence,
            "generic_repetition_pattern": self.generic_repetition_pattern,
            "contextual_name_overlap": self.contextual_name_overlap,
            "contextual_org_overlap": self.contextual_org_overlap,
            "contextual_temporal_overlap": self.contextual_temporal_overlap,
            "contextual_identity_overlap": self.contextual_identity_overlap,
            "contextual_context_overlap": self.contextual_context_overlap,
            "contextual_structure": self.contextual_structure,
            "exposure_score": self.exposure_score,
            "password_score": self.password_score,
            "combined_score": self.combined_score,
            "exposure_band": self.exposure_band.value,
            "password_band": self.password_band.value,
            "primary_action": self.primary_action.value,
            "expected_risk_band": self.expected_risk_band.value,
            "expected_action_floor": self.expected_action_floor.value,
            "expected_action_ceiling": self.expected_action_ceiling.value,
            "within_expected_range": self.within_expected_range,
            "action_severity": self.action_severity,
            "expected_floor_severity": self.expected_floor_severity,
            "expected_ceiling_severity": self.expected_ceiling_severity,
            "action_severity_gap": self.action_severity_gap,
        }


@dataclass
class DatasetOverview:
    """High-level metadata for one generated labeled dataset."""

    organization: str
    seed: int | None
    policy_profile: PolicyProfile
    profile_count: int
    scenario_count: int
    record_count: int
    within_expected_range_rate: float
    risk_band_distribution: dict[str, int]
    action_distribution: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""
        data = asdict(self)
        data["policy_profile"] = self.policy_profile.value
        return data


@dataclass
class DatasetArtifacts:
    """Filesystem artifact references for one saved labeled dataset."""

    run_id: str
    generated_at: str
    output_dir: str
    records_file: str
    overview_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ModelTrainingResult:
    """Metrics and metadata from one model training run."""

    model_type: str
    feature_names: list[str]
    class_labels: list[str]
    train_size: int
    test_size: int
    test_accuracy: float
    heuristic_test_accuracy: float
    accuracy_delta: float
    class_report: dict[str, object]
    feature_importances: dict[str, float] | None
    coefficients: dict[str, list[float]] | None

    def to_dict(self) -> dict[str, object]:
        """Convert training results to a JSON-serializable dictionary."""
        return {
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "class_labels": self.class_labels,
            "train_size": self.train_size,
            "test_size": self.test_size,
            "test_accuracy": self.test_accuracy,
            "heuristic_test_accuracy": self.heuristic_test_accuracy,
            "accuracy_delta": self.accuracy_delta,
            "class_report": self.class_report,
            "feature_importances": self.feature_importances,
            "coefficients": self.coefficients,
        }


@dataclass
class ModelArtifacts:
    """Filesystem artifact references for one saved trained model."""

    run_id: str
    generated_at: str
    output_dir: str
    model_file: str
    metadata_file: str
    model_type: str

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ModelCVResult:
    """Cross-validation accuracy metrics for one model type over a labeled dataset."""

    model_type: str
    n_folds: int
    feature_names: list[str]
    class_labels: list[str]
    record_count: int
    model_accuracy_mean: float
    model_accuracy_std: float
    heuristic_accuracy_mean: float
    heuristic_accuracy_std: float
    accuracy_delta_mean: float
    fold_results: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        """Convert CV results to a JSON-serializable dictionary."""
        return {
            "model_type": self.model_type,
            "n_folds": self.n_folds,
            "feature_names": self.feature_names,
            "class_labels": self.class_labels,
            "record_count": self.record_count,
            "model_accuracy_mean": self.model_accuracy_mean,
            "model_accuracy_std": self.model_accuracy_std,
            "heuristic_accuracy_mean": self.heuristic_accuracy_mean,
            "heuristic_accuracy_std": self.heuristic_accuracy_std,
            "accuracy_delta_mean": self.accuracy_delta_mean,
            "fold_results": self.fold_results,
        }


@dataclass
class ExpertReviewTask:
    """One review task to be sent to a security expert for empirical calibration.

    The reviewer reads ``profile_summary``, sees the candidate ``password``, and
    enters their judgement of the targeted risk band. The heuristic and ML
    bands are included for reference but should not bias the rating.
    """

    task_id: str
    profile_id: str
    scenario_name: str
    profile_summary: str
    password: str
    heuristic_band: RiskBand
    heuristic_action: HardeningAction
    ml_predicted_band: RiskBand | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert the review task to a JSON/CSV-friendly dictionary."""
        return {
            "task_id": self.task_id,
            "profile_id": self.profile_id,
            "scenario_name": self.scenario_name,
            "profile_summary": self.profile_summary,
            "password": self.password,
            "heuristic_band": self.heuristic_band.value,
            "heuristic_action": self.heuristic_action.value,
            "ml_predicted_band": (
                self.ml_predicted_band.value if self.ml_predicted_band is not None else ""
            ),
            "expert_band": "",
            "expert_action": "",
            "notes": "",
        }


@dataclass
class ExpertRating:
    """One completed expert rating for a review task."""

    task_id: str
    profile_id: str
    scenario_name: str
    expert_band: RiskBand
    expert_action: HardeningAction | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        """Convert the rating to a JSON-serializable dictionary."""
        return {
            "task_id": self.task_id,
            "profile_id": self.profile_id,
            "scenario_name": self.scenario_name,
            "expert_band": self.expert_band.value,
            "expert_action": self.expert_action.value if self.expert_action else "",
            "notes": self.notes,
        }


@dataclass
class ExternalCalibrationResult:
    """Three-way comparison of heuristic, ML, and expert calibration."""

    rating_count: int
    heuristic_vs_expert_match_rate: float
    ml_vs_expert_match_rate: float | None
    heuristic_vs_ml_match_rate: float | None
    severe_disagreement_count: int  # heuristic and expert differ by >= 2 bands
    expert_band_distribution: dict[str, int]
    heuristic_band_distribution: dict[str, int]
    ml_band_distribution: dict[str, int] | None
    band_transition_counts: dict[str, int]  # "HEURISTIC→EXPERT" -> count, e.g. "HIGH→CRITICAL"
    disagreement_details: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        """Convert the calibration result to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ReviewerCalibrationSummary:
    """Calibration summary for one completed reviewer CSV."""

    reviewer_id: str
    source_file: str
    rating_count: int
    heuristic_vs_expert_match_rate: float
    ml_vs_expert_match_rate: float | None
    heuristic_vs_ml_match_rate: float | None
    severe_disagreement_count: int

    def to_dict(self) -> dict[str, object]:
        """Convert the reviewer summary to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ConsensusTaskSummary:
    """Consensus band summary for one reviewed (profile, scenario) task."""

    task_id: str
    profile_id: str
    scenario_name: str
    reviewer_count: int
    consensus_band: RiskBand
    vote_counts: dict[str, int]
    reviewer_bands: dict[str, str]
    unanimous: bool
    tie_broken: bool

    def to_dict(self) -> dict[str, object]:
        """Convert the consensus task summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["consensus_band"] = self.consensus_band.value
        return data


@dataclass
class ExpertReviewBatchSummary:
    """Aggregate summary across multiple completed reviewer CSVs."""

    reviewer_count: int
    unique_task_count: int
    mean_tasks_per_reviewer: float
    pairwise_band_agreement_rate: float | None
    unanimous_task_rate: float | None
    average_heuristic_vs_expert_match_rate: float
    average_ml_vs_expert_match_rate: float | None
    average_heuristic_vs_ml_match_rate: float | None
    average_severe_disagreement_count: float
    consensus_result: ExternalCalibrationResult | None

    def to_dict(self) -> dict[str, object]:
        """Convert the batch summary to a JSON-serializable dictionary."""
        data = asdict(self)
        data["consensus_result"] = (
            self.consensus_result.to_dict() if self.consensus_result is not None else None
        )
        return data


@dataclass
class ExpertReviewArtifacts:
    """Filesystem artifact references for one saved expert-review summary bundle."""

    run_id: str
    generated_at: str
    output_dir: str
    summary_file: str
    reviewer_summaries_file: str
    consensus_tasks_file: str
    summary_table_file: str

    def to_dict(self) -> dict[str, object]:
        """Convert artifact references to a JSON-serializable dictionary."""
        return asdict(self)
