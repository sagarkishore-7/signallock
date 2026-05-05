# SignalLock Feature Schema

## Goal

This document defines the first-pass schema for public-profile data, normalized attribute vectors, and policy-relevant metadata. The schema is intentionally conservative and designed for synthetic or authorized data first.

## Design Principles

- keep exposure features separate from password-conditioned features
- prefer normalized tokens over raw free text
- support audit mode and interactive mode with the same base schemas
- minimize fields that could encourage over-collection

## Core Entities

### 1. `PublicProfile`

Represents an organization-approved or synthetic public-facing identity record.

Required fields:

- `employee_id`
- `full_name`
- `title`
- `department`
- `organization`
- `role_seniority`
- `email_format`
- `location`
- `tenure_start_year`
- `platforms`
- `public_usernames`
- `interests`

Optional fields:

- `preferred_name`
- `education`
- `bio`

## Enumerations

### `RoleSeniority`

- `INDIVIDUAL_CONTRIBUTOR`
- `MANAGER`
- `DIRECTOR`
- `VP`
- `C_SUITE`

### `Platform`

- `LINKEDIN`
- `GITHUB`
- `X`
- `PERSONAL_WEBSITE`
- `SPEAKER_BIO`
- `UNIVERSITY_PROFILE`
- `COMPANY_DIRECTORY`

### `RiskBand`

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

### `ExposureAssessment`

- `employee_id`
- `score`
- `band`
- `component_scores`
- `top_factors`

### `PasswordRiskAssessment`

- `employee_id`
- `password_length`
- `score`
- `band`
- `generic_signals`
- `contextual_signals`
- `matched_tokens`
- `top_factors`

### `HardeningAction`

- `ALLOW`
- `WARN`
- `REQUIRE_STRONGER_PASSWORD`
- `ENFORCE_MFA`
- `STEP_UP_AUTHENTICATION`
- `PRIORITIZE_AWARENESS_TRAINING`

### `HardeningRecommendation`

- `employee_id`
- `exposure_score`
- `exposure_band`
- `password_score`
- `password_band`
- `combined_score`
- `policy_profile`
- `primary_action`
- `supporting_actions`
- `rationale`

### `PolicyProfile`

- `balanced`
- `strict`
- `usability`

### `PolicyConfig`

- `profile`
- `exposure_weight`
- `password_weight`
- `warn_threshold`
- `step_up_threshold`
- `enforce_mfa_threshold`
- `awareness_min_exposure_band`
- `step_up_min_exposure_band`
- `enforce_mfa_min_exposure_band`
- `require_stronger_min_password_band`
- `paired_require_stronger_password_band`
- `paired_require_stronger_min_exposure_band`
- `warn_min_password_band`

### `PolicyEvaluationRecord`

- `employee_id`
- `scenario`
- `password`
- `policy_profile`
- `exposure_band`
- `password_band`
- `expected_risk_band`
- `expected_action_floor`
- `expected_action_ceiling`
- `within_expected_range`
- `under_hardening`
- `over_hardening`
- `action_severity_gap`
- `primary_action`
- `combined_score`

### `PolicyEvaluationSummary`

- `policy_profile`
- `sample_count`
- `scenario_count`
- `primary_action_counts`
- `supporting_action_counts`
- `average_combined_score`
- `average_exposure_score`
- `average_password_score`

### `PolicyCalibrationSummary`

- `policy_profile`
- `total_records`
- `high_risk_record_count`
- `low_risk_record_count`
- `floor_action_match_rate`
- `within_expected_range_rate`
- `under_hardening_rate`
- `over_hardening_rate`
- `true_positive_proxy_rate`
- `false_positive_proxy_rate`
- `warn_or_higher_rate`
- `step_up_or_higher_rate`
- `block_or_higher_rate`
- `mean_action_severity_gap`

### `EvaluationArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `report_file`
- `summaries_file`
- `comparison_table_file`
- `calibration_summaries_file`
- `calibration_table_file`
- `records_file`

### `EvaluationRunSummaryRecord`

- `run_id`
- `generated_at`
- `organization`
- `profile_count`
- `seed`
- `policy_profile`
- `sample_count`
- `scenario_count`
- `average_combined_score`
- `average_exposure_score`
- `average_password_score`
- `top_action`
- `source_report_file`

### `EvaluationRunCalibrationRecord`

- `run_id`
- `generated_at`
- `organization`
- `profile_count`
- `seed`
- `policy_profile`
- `total_records`
- `high_risk_record_count`
- `low_risk_record_count`
- `within_expected_range_rate`
- `under_hardening_rate`
- `over_hardening_rate`
- `true_positive_proxy_rate`
- `false_positive_proxy_rate`
- `warn_or_higher_rate`
- `step_up_or_higher_rate`
- `block_or_higher_rate`
- `mean_action_severity_gap`
- `source_report_file`

### `EvaluationRunAnalysisOverview`

- `input_dir`
- `run_count`
- `row_count`
- `policy_profiles`
- `organizations`

### `AnalysisArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `analysis_file`
- `comparison_table_file`
- `policy_matrix_file`
- `calibration_table_file`
- `calibration_matrix_file`

### `PolicyComparisonOverview`

- `input_dir`
- `baseline_profile`
- `candidate_profiles`
- `total_runs_scanned`
- `matched_run_count`
- `summary_count`

### `PolicyComparisonRunDelta`

- `run_id`
- `generated_at`
- `organization`
- `profile_count`
- `seed`
- `baseline_profile`
- `candidate_profile`
- `baseline_top_action`
- `candidate_top_action`
- `action_changed`
- `baseline_combined_score`
- `candidate_combined_score`
- `combined_score_delta`
- `exposure_score_delta`
- `password_score_delta`

### `PolicyComparisonSummary`

- `baseline_profile`
- `candidate_profile`
- `matched_run_count`
- `mean_combined_score_delta`
- `mean_exposure_score_delta`
- `mean_password_score_delta`
- `candidate_higher_combined_ratio`
- `action_change_count`
- `dominant_transition`
- `action_transition_counts`

### `ComparisonArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `summary_file`
- `comparison_table_file`
- `run_deltas_file`
- `delta_chart_file`

### `ExperimentPreset`

- `name`
- `description`
- `organization`
- `profile_count`
- `seeds`
- `policy_profiles`
- `baseline_profile`
- `comparison_candidates`
- `include_records`

### `PresetArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `evaluations_dir`
- `analysis_dir`
- `comparisons_dir`
- `figures_dir`
- `manifest_file`

### `PresetExecutionSummary`

- `preset_name`
- `description`
- `organization`
- `profile_count`
- `seeds`
- `policy_profiles`
- `baseline_profile`
- `comparison_candidates`
- `include_records`
- `generated_at`
- `evaluation_run_count`
- `evaluation_artifacts`
- `analysis_artifacts`
- `comparison_artifacts`
- `figure_artifacts`
- `preset_artifacts`

### `PolicyAggregateRecord`

- `policy_profile`
- `run_count`
- `mean_combined_score`
- `mean_exposure_score`
- `mean_password_score`
- `dominant_top_action`
- `top_action_counts`

### `FigureArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `summary_file`
- `aggregate_csv_file`
- `summary_table_file`
- `score_chart_file`
- `action_chart_file`

### `ThresholdSweepRecord`

- `variant_label`
- `base_profile`
- `threshold_offset`
- `warn_threshold`
- `step_up_threshold`
- `enforce_mfa_threshold`
- `sample_count`
- `scenario_count`
- `average_combined_score`
- `average_exposure_score`
- `average_password_score`
- `top_action`
- `within_expected_range_rate`
- `under_hardening_rate`
- `over_hardening_rate`
- `true_positive_proxy_rate`
- `false_positive_proxy_rate`
- `step_up_or_higher_rate`
- `block_or_higher_rate`
- `mean_action_severity_gap`
- `reference_variant_label`
- `is_reference_variant`
- `top_action_changed_from_reference`
- `within_expected_range_delta`
- `under_hardening_delta`
- `over_hardening_delta`
- `true_positive_proxy_delta`
- `false_positive_proxy_delta`
- `step_up_or_higher_delta`
- `block_or_higher_delta`
- `mean_action_severity_gap_delta`

### `ThresholdSweepOverview`

- `base_profile`
- `organization`
- `profile_count`
- `seed`
- `threshold_offsets`
- `variant_count`
- `policy_file`

### `ThresholdSweepArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `summary_file`
- `records_file`
- `table_file`

### `ThresholdSweepRunRecord`

- `run_id`
- `generated_at`
- `organization`
- `profile_count`
- `seed`
- `base_profile`
- `variant_label`
- `threshold_offset`
- `warn_threshold`
- `step_up_threshold`
- `enforce_mfa_threshold`
- `sample_count`
- `scenario_count`
- `average_combined_score`
- `average_exposure_score`
- `average_password_score`
- `top_action`
- `within_expected_range_rate`
- `under_hardening_rate`
- `over_hardening_rate`
- `true_positive_proxy_rate`
- `false_positive_proxy_rate`
- `step_up_or_higher_rate`
- `block_or_higher_rate`
- `mean_action_severity_gap`
- `reference_variant_label`
- `is_reference_variant`
- `top_action_changed_from_reference`
- `within_expected_range_delta`
- `under_hardening_delta`
- `over_hardening_delta`
- `true_positive_proxy_delta`
- `false_positive_proxy_delta`
- `step_up_or_higher_delta`
- `block_or_higher_delta`
- `mean_action_severity_gap_delta`
- `source_summary_file`

### `ThresholdSweepAggregateRecord`

- `base_profile`
- `threshold_offset`
- `run_count`
- `mean_warn_threshold`
- `mean_step_up_threshold`
- `mean_enforce_mfa_threshold`
- `mean_average_combined_score`
- `mean_within_expected_range_rate`
- `mean_under_hardening_rate`
- `mean_over_hardening_rate`
- `mean_true_positive_proxy_rate`
- `mean_false_positive_proxy_rate`
- `mean_step_up_or_higher_rate`
- `mean_block_or_higher_rate`
- `mean_action_severity_gap`
- `mean_within_expected_range_delta`
- `mean_false_positive_proxy_delta`
- `mean_block_or_higher_delta`
- `dominant_top_action`
- `reference_variant_ratio`
- `top_action_change_rate`

### `ThresholdSweepAnalysisOverview`

- `input_dir`
- `run_count`
- `row_count`
- `aggregate_count`
- `base_profiles`
- `organizations`

### `ThresholdSweepAnalysisArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `summary_file`
- `rows_file`
- `run_table_file`
- `aggregate_file`
- `aggregate_table_file`

### `ThresholdSweepFigureArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `summary_file`
- `aggregate_csv_file`
- `summary_table_file`
- `within_range_chart_file`
- `false_positive_chart_file`
- `action_change_chart_file`

### `PresetRunRecord`

- `preset_run_id`
- `preset_name`
- `description`
- `generated_at`
- `organization`
- `profile_count`
- `evaluation_run_count`
- `seed_count`
- `baseline_profile`
- `policy_profiles`
- `comparison_candidates`
- `output_dir`
- `manifest_file`

### `PresetPolicySummaryRecord`

- `preset_run_id`
- `preset_name`
- `generated_at`
- `organization`
- `profile_count`
- `policy_profile`
- `is_baseline_profile`
- `run_count`
- `mean_combined_score`
- `mean_exposure_score`
- `mean_password_score`
- `dominant_top_action`
- `source_summary_file`

### `PresetCalibrationSummaryRecord`

- `preset_run_id`
- `preset_name`
- `generated_at`
- `organization`
- `profile_count`
- `policy_profile`
- `evaluation_run_count`
- `mean_within_expected_range_rate`
- `mean_under_hardening_rate`
- `mean_over_hardening_rate`
- `mean_true_positive_proxy_rate`
- `mean_false_positive_proxy_rate`
- `mean_step_up_or_higher_rate`
- `mean_block_or_higher_rate`
- `mean_action_severity_gap`
- `source_manifest_file`

### `PresetComparisonSummaryRecord`

- `preset_run_id`
- `preset_name`
- `generated_at`
- `organization`
- `profile_count`
- `baseline_profile`
- `candidate_profile`
- `matched_run_count`
- `mean_combined_score_delta`
- `mean_exposure_score_delta`
- `mean_password_score_delta`
- `candidate_higher_combined_ratio`
- `action_change_count`
- `dominant_transition`
- `source_summary_file`

### `PresetResultsOverview`

- `input_dir`
- `preset_run_count`
- `policy_summary_count`
- `calibration_summary_count`
- `comparison_summary_count`
- `preset_names`
- `organizations`
- `policy_profiles`

### `PresetResultsArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `summary_file`
- `preset_runs_file`
- `policy_summaries_file`
- `calibration_summaries_file`
- `comparison_summaries_file`
- `preset_table_file`
- `policy_table_file`
- `calibration_table_file`
- `comparison_table_file`

### `PresetPolicyAggregateRecord`

- `preset_name`
- `policy_profile`
- `preset_run_count`
- `mean_combined_score`
- `std_combined_score`
- `mean_exposure_score`
- `mean_password_score`
- `dominant_top_action`
- `baseline_run_ratio`

### `PresetCalibrationAggregateRecord`

- `preset_name`
- `policy_profile`
- `preset_run_count`
- `mean_within_expected_range_rate`
- `mean_under_hardening_rate`
- `mean_over_hardening_rate`
- `mean_true_positive_proxy_rate`
- `mean_false_positive_proxy_rate`
- `mean_step_up_or_higher_rate`
- `mean_block_or_higher_rate`
- `mean_action_severity_gap`

### `PresetComparisonAggregateRecord`

- `preset_name`
- `baseline_profile`
- `candidate_profile`
- `preset_run_count`
- `mean_combined_score_delta`
- `std_combined_score_delta`
- `mean_exposure_score_delta`
- `mean_password_score_delta`
- `mean_candidate_higher_ratio`
- `mean_action_change_ratio`
- `dominant_transition`

### `CrossPresetPolicyAggregateRecord`

- `policy_profile`
- `preset_name_count`
- `preset_run_count`
- `mean_combined_score`
- `std_combined_score`
- `mean_exposure_score`
- `mean_password_score`
- `dominant_top_action`

### `CrossPresetCalibrationAggregateRecord`

- `policy_profile`
- `preset_name_count`
- `preset_run_count`
- `mean_within_expected_range_rate`
- `mean_under_hardening_rate`
- `mean_over_hardening_rate`
- `mean_true_positive_proxy_rate`
- `mean_false_positive_proxy_rate`
- `mean_step_up_or_higher_rate`
- `mean_block_or_higher_rate`
- `mean_action_severity_gap`

### `CrossPresetComparisonAggregateRecord`

- `baseline_profile`
- `candidate_profile`
- `preset_name_count`
- `preset_run_count`
- `mean_combined_score_delta`
- `std_combined_score_delta`
- `mean_exposure_score_delta`
- `mean_password_score_delta`
- `mean_candidate_higher_ratio`
- `mean_action_change_ratio`
- `dominant_transition`

### `PresetAggregateOverview`

- `input_dir`
- `preset_run_count`
- `preset_policy_aggregate_count`
- `preset_calibration_aggregate_count`
- `preset_comparison_aggregate_count`
- `cross_policy_aggregate_count`
- `cross_calibration_aggregate_count`
- `cross_comparison_aggregate_count`
- `preset_names`
- `policy_profiles`

### `PresetAggregateArtifacts`

- `run_id`
- `generated_at`
- `output_dir`
- `summary_file`
- `preset_policy_csv_file`
- `preset_calibration_csv_file`
- `preset_comparison_csv_file`
- `cross_policy_csv_file`
- `cross_calibration_csv_file`
- `cross_comparison_csv_file`
- `preset_policy_table_file`
- `preset_calibration_table_file`
- `preset_comparison_table_file`
- `cross_policy_table_file`
- `cross_calibration_table_file`
- `cross_comparison_table_file`

## Exposure-Oriented Fields

These features should influence exposure scoring, not password scoring by themselves.

- `role_seniority`
- `department`
- `platform_count`
- `platform_diversity`
- `title_visibility`
- `public_year_markers`
- `organization_visibility`
- `bio_richness`
- `username_count`

## Password-Conditioned Fields

These features are computed only when a candidate password is present.

- overlap with full-name tokens
- overlap with preferred-name tokens
- overlap with public usernames
- overlap with organization tokens
- overlap with year markers
- overlap with location tokens
- overlap with interests
- presence of common contextual structures such as name-plus-year or org-plus-symbol
- generic weakness features such as short length, low character diversity, repetition, and simple sequences

## Token Categories

The first implementation should normalize these token sets:

### Name Tokens

- first name
- last name
- preferred name
- common shortened forms when explicitly available

### Organization Tokens

- organization name words
- department words
- title keywords

### Temporal Tokens

- tenure start year
- graduation year if available
- other explicitly public year markers

### Identity Tokens

- usernames
- email local-part patterns

### Context Tokens

- city or location words
- interest or hobby keywords
- education institution tokens

## Minimal Validation Rules

- `employee_id` must be non-empty
- `full_name` must contain visible characters
- `tenure_start_year` must be between `1970` and `2100`
- `platforms` may be empty only in explicitly low-exposure synthetic cases
- `public_usernames` should be unique after normalization
- `interests` should be deduplicated after normalization

## Normalization Rules

- trim whitespace
- store token lists in lowercase for feature extraction
- remove empty list items
- keep the original display form only where needed for user-facing output

## Phase 1 Synthetic Data Coverage

Each synthetic profile should vary along:

- role seniority
- department
- organization type
- city / geography
- number of public platforms
- username style
- year-marker presence
- interest profile

This creates enough structured variation to start testing exposure and password-conditioning logic.

## Future Schema Extensions

Possible later additions:

- richer relationship graphs
- organization-specific naming conventions
- language or locale metadata
- explanation objects
- experiment metadata and plotting schemas

Those should be added only after the core profile schema is stable.

## Current Prototype Note

The current implementation already supports:

- `PublicProfile`
- `AttributeVector`
- `ExposureAssessment`
- `PasswordRiskAssessment`
- `HardeningRecommendation`
- `PolicyConfig`
- `PolicyEvaluationRecord`
- `PolicyEvaluationSummary`
- `PolicyCalibrationSummary`
- `EvaluationArtifacts`
- `EvaluationRunSummaryRecord`
- `EvaluationRunCalibrationRecord`
- `EvaluationRunAnalysisOverview`
- `AnalysisArtifacts`
- `PolicyComparisonOverview`
- `PolicyComparisonRunDelta`
- `PolicyComparisonSummary`
- `ComparisonArtifacts`
- `ExperimentPreset`
- `PresetArtifacts`
- `PresetExecutionSummary`
- `PolicyAggregateRecord`
- `FigureArtifacts`
- `PresetRunRecord`
- `PresetPolicySummaryRecord`
- `PresetCalibrationSummaryRecord`
- `PresetComparisonSummaryRecord`
- `PresetResultsOverview`
- `PresetResultsArtifacts`
- `PresetPolicyAggregateRecord`
- `PresetCalibrationAggregateRecord`
- `PresetComparisonAggregateRecord`
- `CrossPresetPolicyAggregateRecord`
- `CrossPresetCalibrationAggregateRecord`
- `CrossPresetComparisonAggregateRecord`
- `PresetAggregateOverview`
- `PresetAggregateArtifacts`
- `ThresholdSweepRecord`
- `ThresholdSweepOverview`
- `ThresholdSweepArtifacts`
- `ThresholdSweepRunRecord`
- `ThresholdSweepAggregateRecord`
- `ThresholdSweepAnalysisOverview`
- `ThresholdSweepAnalysisArtifacts`
- `ThresholdSweepFigureArtifacts`

The scoring outputs remain heuristic baselines and should be treated as transparent placeholders pending later calibration and evaluation.

The current evaluation layer does support proxy calibration targets for synthetic scenarios, but these are intentionally synthetic expectations rather than real-user labels.
