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
