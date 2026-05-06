"""CLI entrypoint for the SignalLock project."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .analysis import (
    analysis_results_to_json,
    analyze_evaluation_calibration_runs,
    analyze_evaluation_runs,
    render_run_calibration_table,
    render_run_analysis_table,
    write_run_analysis_artifacts,
)
from .comparison import (
    compare_policy_profiles,
    comparison_results_to_json,
    render_policy_comparison_table as render_policy_delta_table,
    write_policy_comparison_artifacts,
)
from .evaluation import (
    evaluate_policy_profiles,
    evaluation_results_to_json,
    summarize_policy_calibration,
)
from .dataset import (
    DEFAULT_DATASET_OUTPUT_DIR,
    dataset_results_to_json,
    generate_dataset,
    write_dataset_artifacts,
)
from .model import (
    DEFAULT_MODEL_OUTPUT_DIR,
    save_model,
    train_model,
    train_model_cv,
    training_results_to_json,
)
from .model_integration import compare_scoring, comparison_to_json
from .expert_review import (
    calibration_result_to_json,
    compute_external_calibration,
    expert_review_batch_to_json,
    extract_ml_predicted_bands_csv,
    generate_review_tasks,
    import_expert_ratings_csv,
    render_expert_review_summary_table,
    summarize_expert_review_batch,
    write_expert_review_artifacts,
    write_review_tasks_csv,
    write_review_tasks_json,
)
from .explanation import explain_recommendation, explanation_to_json
from .exposure import assessments_to_json, score_profiles_exposure
from .figures import (
    aggregate_policy_rows,
    figure_results_to_json,
    render_policy_aggregate_table,
    write_figure_artifacts,
)
from .password_risk import score_password_for_profile
from .policy import get_policy_config, policy_configs_to_json, recommend_hardening
from .preset_aggregates import (
    DEFAULT_PRESET_AGGREGATE_OUTPUT_DIR,
    aggregate_preset_results,
    preset_aggregate_results_to_json,
    write_preset_aggregate_artifacts,
)
from .presets import execute_preset, get_preset, presets_to_json
from .sweep_presets import (
    execute_sweep_preset,
    get_sweep_preset,
    sweep_preset_execution_to_json,
    sweep_presets_to_json,
)
from .reporting import (
    DEFAULT_EVALUATION_OUTPUT_DIR,
    render_policy_calibration_table,
    render_policy_comparison_table as render_evaluation_comparison_table,
    write_evaluation_artifacts,
)
from .results import (
    DEFAULT_PRESET_INPUT_DIR,
    preset_results_to_json,
    render_preset_calibration_table,
    render_preset_comparison_table,
    render_preset_policy_table,
    render_preset_run_table,
    summarize_preset_runs,
    write_preset_results_artifacts,
)
from .schemas import PolicyProfile
from .synthetic_profiles import generate_synthetic_profiles, profiles_to_json
from .threshold_sweeps import (
    DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR,
    run_threshold_sweep,
    threshold_sweep_results_to_json,
    write_threshold_sweep_artifacts,
)
from .threshold_sweep_analysis import (
    DEFAULT_THRESHOLD_SWEEP_ANALYSIS_OUTPUT_DIR,
    analyze_threshold_sweeps,
    render_threshold_sweep_aggregate_table,
    render_threshold_sweep_run_table,
    threshold_sweep_analysis_to_json,
    write_threshold_sweep_analysis_artifacts,
)
from .threshold_sweep_figures import (
    DEFAULT_THRESHOLD_SWEEP_FIGURE_OUTPUT_DIR,
    threshold_sweep_figure_results_to_json,
    write_threshold_sweep_figure_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level command parser."""
    parser = argparse.ArgumentParser(
        prog="signallock",
        description=(
            "SignalLock: OSINT-calibrated password risk assessment and "
            "context-aware enterprise authentication hardening."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser(
        "generate-profiles",
        help="Generate synthetic public profiles for Phase 1 development.",
    )
    generate_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of synthetic profiles to generate.",
    )
    generate_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    generate_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    generate_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    score_parser = subparsers.add_parser(
        "score-exposure",
        help="Generate synthetic profiles and score their baseline exposure.",
    )
    score_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of synthetic profiles to generate.",
    )
    score_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    score_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    score_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    password_parser = subparsers.add_parser(
        "score-password",
        help="Score a candidate password against a synthetic public profile context.",
    )
    password_parser.add_argument(
        "--password",
        required=True,
        help="Candidate password to assess.",
    )
    password_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of synthetic profiles to generate.",
    )
    password_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    password_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    password_parser.add_argument(
        "--profile-index",
        type=int,
        default=0,
        help="Zero-based synthetic profile index to use as context.",
    )
    password_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    policy_parser = subparsers.add_parser(
        "recommend-hardening",
        help="Generate a hardening recommendation from exposure and password risk.",
    )
    policy_parser.add_argument(
        "--password",
        required=True,
        help="Candidate password to assess.",
    )
    policy_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of synthetic profiles to generate.",
    )
    policy_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    policy_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    policy_parser.add_argument(
        "--profile-index",
        type=int,
        default=0,
        help="Zero-based synthetic profile index to use as context.",
    )
    policy_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    policy_parser.add_argument(
        "--policy-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Named hardening policy profile to apply.",
    )
    policy_parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional path to a policy profile JSON file.",
    )
    policy_parser.add_argument(
        "--model-file",
        default=None,
        help="Optional path to a trained model .pkl file. When supplied, the ML-predicted risk band replaces the heuristic band in policy decisions.",
    )

    compare_parser = subparsers.add_parser(
        "compare-scoring",
        help="Show heuristic vs ML-assisted scoring side by side for one (profile, password) pair.",
    )
    compare_parser.add_argument("--password", required=True, help="Candidate password to assess.")
    compare_parser.add_argument("--count", type=int, default=5, help="Number of synthetic profiles to generate.")
    compare_parser.add_argument("--organization", default="ExampleCorp", help="Organization name.")
    compare_parser.add_argument("--seed", type=int, default=None, help="Optional random seed.")
    compare_parser.add_argument("--profile-index", type=int, default=0, help="Zero-based synthetic profile index.")
    compare_parser.add_argument(
        "--model-file",
        required=True,
        help="Path to a trained model .pkl file produced by train-model.",
    )
    compare_parser.add_argument(
        "--policy-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Named hardening policy profile to apply.",
    )
    compare_parser.add_argument("--policy-file", default=None, help="Optional path to a policy profile JSON file.")
    compare_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    review_parser = subparsers.add_parser(
        "generate-review-tasks",
        help="Export review tasks (one per profile-scenario pair) for security expert calibration.",
    )
    review_parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of synthetic profiles to generate.",
    )
    review_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    review_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    review_parser.add_argument(
        "--policy-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Policy profile used to derive the heuristic-action reference column.",
    )
    review_parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional path to a policy profile JSON file.",
    )
    review_parser.add_argument(
        "--model-file",
        default=None,
        help="Optional path to a trained model .pkl file. When supplied, the exported tasks include ml_predicted_band values.",
    )
    review_parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format. CSV is Excel-friendly; JSON preserves structure.",
    )
    review_parser.add_argument(
        "--output-file",
        default=None,
        help="Path to write the export to. If omitted, prints to stdout.",
    )
    review_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (only applies to --format json).",
    )

    calibration_parser = subparsers.add_parser(
        "compute-external-calibration",
        help="Cross-reference expert ratings with heuristic and (optional) ML predictions.",
    )
    calibration_parser.add_argument(
        "--records-file",
        required=True,
        help="Path to a dataset_records.csv produced by generate-dataset.",
    )
    calibration_parser.add_argument(
        "--ratings-file",
        required=True,
        help="Path to a completed review CSV with expert_band filled in.",
    )
    calibration_parser.add_argument(
        "--model-file",
        default=None,
        help=(
            "Optional path to the trained model used when generating the review packet. "
            "When supplied, the ratings CSV is expected to already contain ml_predicted_band values."
        ),
    )
    calibration_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    review_summary_parser = subparsers.add_parser(
        "summarize-expert-reviews",
        help="Aggregate multiple completed reviewer CSVs into per-reviewer and consensus summaries.",
    )
    review_summary_parser.add_argument(
        "--records-file",
        required=True,
        help="Path to a dataset_records.csv produced by generate-dataset.",
    )
    review_summary_parser.add_argument(
        "--ratings-files",
        nargs="+",
        required=True,
        help="One or more completed reviewer CSV files.",
    )
    review_summary_parser.add_argument(
        "--model-file",
        default=None,
        help=(
            "Optional path to the trained model used when generating the review packets. "
            "When supplied, each ratings CSV is expected to contain ml_predicted_band values."
        ),
    )
    review_summary_parser.add_argument(
        "--include-reviewer-summaries",
        action="store_true",
        help="Include per-reviewer calibration summaries in the JSON output.",
    )
    review_summary_parser.add_argument(
        "--include-consensus-tasks",
        action="store_true",
        help="Include per-task consensus summaries in the JSON output.",
    )
    review_summary_parser.add_argument(
        "--include-table",
        action="store_true",
        help="Include a markdown reviewer summary table in the JSON output.",
    )
    review_summary_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Persist the expert-review summary bundle under artifacts/expert_review/.",
    )
    review_summary_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for saved expert-review summary artifacts.",
    )
    review_summary_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    profiles_parser = subparsers.add_parser(
        "list-policy-profiles",
        help="List built-in hardening policy profiles and thresholds.",
    )
    profiles_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    profiles_parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional path to a policy profile JSON file.",
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate-policies",
        help="Compare policy profiles across synthetic profiles and scenarios.",
    )
    evaluate_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of synthetic profiles to generate.",
    )
    evaluate_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    evaluate_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    evaluate_parser.add_argument(
        "--policy-profiles",
        nargs="*",
        choices=[profile.value for profile in PolicyProfile],
        default=None,
        help="Optional subset of policy profiles to evaluate.",
    )
    evaluate_parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional path to a policy profile JSON file.",
    )
    evaluate_parser.add_argument(
        "--include-records",
        action="store_true",
        help="Include per-scenario evaluation records in the JSON output.",
    )
    evaluate_parser.add_argument(
        "--include-table",
        action="store_true",
        help="Include a markdown comparison table in the JSON output.",
    )
    evaluate_parser.add_argument(
        "--save-run",
        action="store_true",
        help="Write a timestamped evaluation artifact bundle to disk.",
    )
    evaluate_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for saved evaluation artifacts.",
    )
    evaluate_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    analyze_parser = subparsers.add_parser(
        "analyze-runs",
        help="Aggregate saved evaluation runs into cross-run comparison outputs.",
    )
    analyze_parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_EVALUATION_OUTPUT_DIR),
        help="Directory containing saved evaluation run subdirectories.",
    )
    analyze_parser.add_argument(
        "--policy-profiles",
        nargs="*",
        choices=[profile.value for profile in PolicyProfile],
        default=None,
        help="Optional subset of policy profiles to include in the analysis.",
    )
    analyze_parser.add_argument(
        "--include-rows",
        action="store_true",
        help="Include flattened per-run rows in the JSON output.",
    )
    analyze_parser.add_argument(
        "--include-table",
        action="store_true",
        help="Include a markdown comparison table in the JSON output.",
    )
    analyze_parser.add_argument(
        "--save-analysis",
        action="store_true",
        help="Write a timestamped cross-run analysis bundle to disk.",
    )
    analyze_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for saved analysis artifacts.",
    )
    analyze_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    figures_parser = subparsers.add_parser(
        "generate-figures",
        help="Generate aggregate SVG and CSV figures from saved evaluation runs.",
    )
    figures_parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_EVALUATION_OUTPUT_DIR),
        help="Directory containing saved evaluation run subdirectories.",
    )
    figures_parser.add_argument(
        "--policy-profiles",
        nargs="*",
        choices=[profile.value for profile in PolicyProfile],
        default=None,
        help="Optional subset of policy profiles to include in the figure bundle.",
    )
    figures_parser.add_argument(
        "--include-aggregates",
        action="store_true",
        help="Include aggregated policy metrics in the JSON output.",
    )
    figures_parser.add_argument(
        "--include-table",
        action="store_true",
        help="Include a markdown policy summary table in the JSON output.",
    )
    figures_parser.add_argument(
        "--save-figures",
        action="store_true",
        help="Write a timestamped SVG/CSV figure bundle to disk.",
    )
    figures_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for saved figure artifacts.",
    )
    figures_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    compare_parser = subparsers.add_parser(
        "compare-policies",
        help="Compare one baseline policy profile against candidate profiles across saved runs.",
    )
    compare_parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_EVALUATION_OUTPUT_DIR),
        help="Directory containing saved evaluation run subdirectories.",
    )
    compare_parser.add_argument(
        "--baseline-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Baseline policy profile to compare against.",
    )
    compare_parser.add_argument(
        "--candidate-profiles",
        nargs="*",
        choices=[profile.value for profile in PolicyProfile],
        default=None,
        help="Optional candidate policy profiles to compare against the baseline.",
    )
    compare_parser.add_argument(
        "--include-run-deltas",
        action="store_true",
        help="Include per-run policy deltas in the JSON output.",
    )
    compare_parser.add_argument(
        "--include-table",
        action="store_true",
        help="Include a markdown comparison table in the JSON output.",
    )
    compare_parser.add_argument(
        "--save-comparison",
        action="store_true",
        help="Write a timestamped comparison bundle to disk.",
    )
    compare_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for saved comparison artifacts.",
    )
    compare_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    presets_parser = subparsers.add_parser(
        "list-experiment-presets",
        help="List built-in experiment presets for repeatable research workflows.",
    )
    presets_parser.add_argument(
        "--preset-file",
        default=None,
        help="Optional path to an experiment preset JSON file.",
    )
    presets_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    run_preset_parser = subparsers.add_parser(
        "run-preset",
        help="Execute a named experiment preset and save a full artifact bundle.",
    )
    run_preset_parser.add_argument(
        "--preset",
        required=True,
        help="Name of the preset to execute.",
    )
    run_preset_parser.add_argument(
        "--preset-file",
        default=None,
        help="Optional path to an experiment preset JSON file.",
    )
    run_preset_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for the saved preset bundle.",
    )
    run_preset_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    summarize_presets_parser = subparsers.add_parser(
        "summarize-presets",
        help="Summarize executed preset bundles into thesis-friendly tables and CSV artifacts.",
    )
    summarize_presets_parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRESET_INPUT_DIR),
        help="Directory containing saved preset run subdirectories.",
    )
    summarize_presets_parser.add_argument(
        "--preset-names",
        nargs="*",
        default=None,
        help="Optional subset of preset names to include in the summary.",
    )
    summarize_presets_parser.add_argument(
        "--include-runs",
        action="store_true",
        help="Include flattened preset-run records in the JSON output.",
    )
    summarize_presets_parser.add_argument(
        "--include-policy-summaries",
        action="store_true",
        help="Include per-policy preset summaries in the JSON output.",
    )
    summarize_presets_parser.add_argument(
        "--include-comparison-summaries",
        action="store_true",
        help="Include per-candidate preset comparison summaries in the JSON output.",
    )
    summarize_presets_parser.add_argument(
        "--include-tables",
        action="store_true",
        help="Include markdown summary tables in the JSON output.",
    )
    summarize_presets_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Write a timestamped preset-results summary bundle to disk.",
    )
    summarize_presets_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for saved preset-results artifacts.",
    )
    summarize_presets_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    aggregate_presets_parser = subparsers.add_parser(
        "aggregate-presets",
        help="Aggregate preset summaries into paper-style cross-preset result tables.",
    )
    aggregate_presets_parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRESET_INPUT_DIR),
        help="Directory containing saved preset run subdirectories.",
    )
    aggregate_presets_parser.add_argument(
        "--preset-names",
        nargs="*",
        default=None,
        help="Optional subset of preset names to include in the aggregation.",
    )
    aggregate_presets_parser.add_argument(
        "--include-tables",
        action="store_true",
        help="Include markdown aggregate tables in the JSON output.",
    )
    aggregate_presets_parser.add_argument(
        "--save-aggregates",
        action="store_true",
        help="Write a timestamped preset aggregate bundle to disk.",
    )
    aggregate_presets_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PRESET_AGGREGATE_OUTPUT_DIR),
        help="Optional directory for saved preset aggregate artifacts.",
    )
    aggregate_presets_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    threshold_sweep_parser = subparsers.add_parser(
        "sweep-thresholds",
        help="Run a calibration sensitivity study by shifting policy score thresholds.",
    )
    threshold_sweep_parser.add_argument(
        "--base-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Base policy profile to perturb.",
    )
    threshold_sweep_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of synthetic profiles to generate.",
    )
    threshold_sweep_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    threshold_sweep_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    threshold_sweep_parser.add_argument(
        "--threshold-offsets",
        nargs="*",
        type=float,
        default=[-12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0],
        help="Additive offsets applied to warn/step-up/enforce thresholds.",
    )
    threshold_sweep_parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional path to a policy profile JSON file.",
    )
    threshold_sweep_parser.add_argument(
        "--include-table",
        action="store_true",
        help="Include a markdown sweep table in the JSON output.",
    )
    threshold_sweep_parser.add_argument(
        "--save-sweep",
        action="store_true",
        help="Write a timestamped threshold-sweep bundle to disk.",
    )
    threshold_sweep_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR),
        help="Optional directory for saved threshold-sweep artifacts.",
    )
    threshold_sweep_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    threshold_sweep_analysis_parser = subparsers.add_parser(
        "analyze-threshold-sweeps",
        help="Aggregate saved threshold-sweep bundles into cross-run sensitivity outputs.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR),
        help="Directory containing saved threshold-sweep subdirectories.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--base-profiles",
        nargs="*",
        choices=[profile.value for profile in PolicyProfile],
        default=None,
        help="Optional subset of base policy profiles to include in the analysis.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--include-rows",
        action="store_true",
        help="Include flattened threshold-sweep rows in the JSON output.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--include-aggregates",
        action="store_true",
        help="Include aggregated threshold-sweep rows in the JSON output.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--include-tables",
        action="store_true",
        help="Include markdown run and aggregate tables in the JSON output.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--save-analysis",
        action="store_true",
        help="Write a timestamped threshold-sweep analysis bundle to disk.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_THRESHOLD_SWEEP_ANALYSIS_OUTPUT_DIR),
        help="Optional directory for saved threshold-sweep analysis artifacts.",
    )
    threshold_sweep_analysis_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    threshold_sweep_figures_parser = subparsers.add_parser(
        "generate-threshold-sweep-figures",
        help="Generate SVG and CSV figures from saved threshold-sweep bundles.",
    )
    threshold_sweep_figures_parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_THRESHOLD_SWEEP_OUTPUT_DIR),
        help="Directory containing saved threshold-sweep subdirectories.",
    )
    threshold_sweep_figures_parser.add_argument(
        "--base-profiles",
        nargs="*",
        choices=[profile.value for profile in PolicyProfile],
        default=None,
        help="Optional subset of base policy profiles to include in the figure bundle.",
    )
    threshold_sweep_figures_parser.add_argument(
        "--include-aggregates",
        action="store_true",
        help="Include aggregated threshold-sweep rows in the JSON output.",
    )
    threshold_sweep_figures_parser.add_argument(
        "--include-table",
        action="store_true",
        help="Include a markdown threshold-sweep summary table in the JSON output.",
    )
    threshold_sweep_figures_parser.add_argument(
        "--save-figures",
        action="store_true",
        help="Write a timestamped threshold-sweep figure bundle to disk.",
    )
    threshold_sweep_figures_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_THRESHOLD_SWEEP_FIGURE_OUTPUT_DIR),
        help="Optional directory for saved threshold-sweep figure artifacts.",
    )
    threshold_sweep_figures_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    train_parser = subparsers.add_parser(
        "train-model",
        help=(
            "Train a scikit-learn risk-band classifier on a labeled dataset. "
            "Requires: pip install signallock[ml]"
        ),
    )
    _train_source = train_parser.add_mutually_exclusive_group(required=True)
    _train_source.add_argument(
        "--input-file",
        default=None,
        help="Path to a dataset_records.csv file produced by generate-dataset.",
    )
    _train_source.add_argument(
        "--count",
        type=int,
        default=None,
        help="Generate a dataset inline from this many synthetic profiles.",
    )
    train_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name (used only with --count).",
    )
    train_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible dataset generation (used only with --count).",
    )
    train_parser.add_argument(
        "--policy-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Policy profile for action labels (used only with --count).",
    )
    train_parser.add_argument(
        "--model-type",
        choices=["logistic", "gradient_boosting"],
        default="gradient_boosting",
        help="Estimator type to train.",
    )
    train_parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of records held out for evaluation (default 0.2).",
    )
    train_parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random state for train/test split and model.",
    )
    train_parser.add_argument(
        "--folds",
        type=int,
        default=None,
        help="Run stratified k-fold cross-validation with this many folds instead of a single train-test split. Disables --save-model.",
    )
    train_parser.add_argument(
        "--save-model",
        action="store_true",
        help="Persist the trained model and metadata to disk (ignored when --folds is set).",
    )
    train_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_MODEL_OUTPUT_DIR),
        help="Directory for saved model artifacts.",
    )
    train_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    dataset_parser = subparsers.add_parser(
        "generate-dataset",
        help="Generate a labeled feature-matrix dataset for ML training and calibration analysis.",
    )
    dataset_parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of synthetic profiles to generate.",
    )
    dataset_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    dataset_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    dataset_parser.add_argument(
        "--policy-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Policy profile used to derive primary-action labels.",
    )
    dataset_parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional path to a policy profile JSON file.",
    )
    dataset_parser.add_argument(
        "--include-records",
        action="store_true",
        help="Include the full record list in the JSON output.",
    )
    dataset_parser.add_argument(
        "--save-dataset",
        action="store_true",
        help="Write the dataset CSV and overview JSON to disk.",
    )
    dataset_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_DATASET_OUTPUT_DIR),
        help="Directory for saved dataset artifacts.",
    )
    dataset_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    explain_parser = subparsers.add_parser(
        "explain-recommendation",
        help="Produce a human-readable explanation of an exposure and password risk assessment.",
    )
    explain_parser.add_argument(
        "--password",
        required=True,
        help="Candidate password to assess.",
    )
    explain_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of synthetic profiles to generate.",
    )
    explain_parser.add_argument(
        "--organization",
        default="ExampleCorp",
        help="Organization name to embed in generated profiles.",
    )
    explain_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    explain_parser.add_argument(
        "--profile-index",
        type=int,
        default=0,
        help="Zero-based synthetic profile index to use as context.",
    )
    explain_parser.add_argument(
        "--policy-profile",
        choices=[profile.value for profile in PolicyProfile],
        default=PolicyProfile.BALANCED.value,
        help="Named hardening policy profile to apply.",
    )
    explain_parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional path to a policy profile JSON file.",
    )
    explain_parser.add_argument(
        "--model-file",
        default=None,
        help="Optional path to a trained model .pkl file. When supplied, the ML-predicted risk band replaces the heuristic band before the explanation is rendered.",
    )
    explain_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    list_sweep_presets_parser = subparsers.add_parser(
        "list-sweep-presets",
        help="List built-in threshold-sweep presets for repeatable sensitivity studies.",
    )
    list_sweep_presets_parser.add_argument(
        "--sweep-preset-file",
        default=None,
        help="Optional path to a threshold-sweep preset JSON file.",
    )
    list_sweep_presets_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    run_sweep_preset_parser = subparsers.add_parser(
        "run-sweep-preset",
        help="Execute a named threshold-sweep preset across multiple seeds and base profiles.",
    )
    run_sweep_preset_parser.add_argument(
        "--preset",
        required=True,
        help="Name of the sweep preset to execute.",
    )
    run_sweep_preset_parser.add_argument(
        "--sweep-preset-file",
        default=None,
        help="Optional path to a threshold-sweep preset JSON file.",
    )
    run_sweep_preset_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for the saved sweep preset bundle.",
    )
    run_sweep_preset_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help=(
            "Start the SignalLock FastAPI service for Audit and Interactive modes. "
            "Requires: pip install signallock[api]"
        ),
    )
    serve_parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Bind address. Defaults to $HOST or 127.0.0.1 (loopback only). Use 0.0.0.0 for production hosting.",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="TCP port to listen on. Defaults to $PORT or 8000.",
    )
    serve_parser.add_argument(
        "--model-file",
        default=os.environ.get("MODEL_FILE"),
        help="Optional path to a trained model .pkl file. Defaults to $MODEL_FILE. Enables /compare-scoring and ?ml=true.",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (development only).",
    )
    serve_parser.add_argument(
        "--cors-origins",
        nargs="*",
        default=(os.environ.get("CORS_ORIGINS", "").split() or None),
        help="Allowed CORS origins (e.g. http://localhost:3000). Defaults to $CORS_ORIGINS (space-separated).",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the SignalLock CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate-profiles":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        print(profiles_to_json(profiles, pretty=args.pretty))
        return

    if args.command == "score-exposure":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        assessments = score_profiles_exposure(profiles)
        print(assessments_to_json(assessments, pretty=args.pretty))
        return

    if args.command == "score-password":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        if args.profile_index < 0 or args.profile_index >= len(profiles):
            parser.error("--profile-index must refer to a generated synthetic profile")

        profile = profiles[args.profile_index]
        assessment = score_password_for_profile(args.password, profile)
        payload = {
            "profile": profile.to_dict(),
            "assessment": assessment.to_dict(),
        }
        if args.pretty:
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload))
        return

    if args.command == "recommend-hardening":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        if args.profile_index < 0 or args.profile_index >= len(profiles):
            parser.error("--profile-index must refer to a generated synthetic profile")

        profile = profiles[args.profile_index]
        exposure = score_profiles_exposure([profile])[0]
        password_assessment = score_password_for_profile(args.password, profile)
        config = get_policy_config(args.policy_profile, policy_file=args.policy_file)

        predicted_band = None
        if args.model_file:
            from .exposure import profile_to_attribute_vector
            from .model import load_model_artifacts, predict_risk_band as _predict

            vector = profile_to_attribute_vector(profile)
            fitted_model, _ = load_model_artifacts(args.model_file)
            predicted_band = _predict(fitted_model, vector, password_assessment)

        recommendation = recommend_hardening(
            exposure,
            password_assessment,
            config=config,
            predicted_password_band=predicted_band,
        )
        payload = {
            "profile": profile.to_dict(),
            "exposure": exposure.to_dict(),
            "password_assessment": password_assessment.to_dict(),
            "policy_config": config.to_dict(),
            "recommendation": recommendation.to_dict(),
        }
        if args.pretty:
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload))
        return

    if args.command == "compare-scoring":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        if args.profile_index < 0 or args.profile_index >= len(profiles):
            parser.error("--profile-index must refer to a generated synthetic profile")

        profile = profiles[args.profile_index]
        config = get_policy_config(args.policy_profile, policy_file=args.policy_file)
        comparison = compare_scoring(args.password, profile, args.model_file, config=config)
        print(comparison_to_json(comparison, pretty=args.pretty))
        return

    if args.command == "generate-review-tasks":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        tasks = generate_review_tasks(
            profiles,
            policy_profile=PolicyProfile(args.policy_profile),
            policy_file=args.policy_file,
            model_file=args.model_file,
        )
        if args.format == "csv":
            output = write_review_tasks_csv(tasks)
        else:
            output = write_review_tasks_json(tasks, pretty=args.pretty)
        if args.output_file:
            Path(args.output_file).write_text(output, encoding="utf-8")
            print(json.dumps({"tasks_written": len(tasks), "output_file": args.output_file}))
        else:
            print(output)
        return

    if args.command == "compute-external-calibration":
        from .dataset import _csv_rows_to_records as _rows_to_records
        import csv as _csv

        with open(args.records_file, newline="", encoding="utf-8") as fh:
            records = _rows_to_records(list(_csv.DictReader(fh)))
        ratings = import_expert_ratings_csv(args.ratings_file)
        ml_bands = extract_ml_predicted_bands_csv(args.ratings_file) or None
        if args.model_file and ml_bands is None:
            parser.error(
                "ratings CSV does not contain ml_predicted_band values. "
                "Regenerate the review packet with generate-review-tasks --model-file "
                "using the same trained model, then re-run compute-external-calibration."
            )

        result = compute_external_calibration(records, ratings, ml_predicted_bands=ml_bands)
        print(calibration_result_to_json(result, pretty=args.pretty))
        return

    if args.command == "summarize-expert-reviews":
        from .dataset import _csv_rows_to_records as _rows_to_records
        import csv as _csv

        with open(args.records_file, newline="", encoding="utf-8") as fh:
            records = _rows_to_records(list(_csv.DictReader(fh)))

        try:
            overview, reviewer_summaries, consensus_tasks = summarize_expert_review_batch(
                records,
                args.ratings_files,
                require_ml_reference=args.model_file is not None,
            )
        except ValueError as exc:
            parser.error(str(exc))

        summary_table = (
            render_expert_review_summary_table(overview, reviewer_summaries)
            if args.include_table or args.save_summary
            else None
        )
        artifacts = None
        if args.save_summary:
            artifacts = write_expert_review_artifacts(
                overview,
                reviewer_summaries,
                consensus_tasks,
                output_dir=args.output_dir,
            )

        print(
            expert_review_batch_to_json(
                overview,
                reviewer_summaries,
                consensus_tasks,
                include_reviewer_summaries=args.include_reviewer_summaries,
                include_consensus_tasks=args.include_consensus_tasks,
                pretty=args.pretty,
                summary_table_markdown=summary_table if args.include_table else None,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "list-policy-profiles":
        print(policy_configs_to_json(pretty=args.pretty, policy_file=args.policy_file))
        return

    if args.command == "list-experiment-presets":
        print(presets_to_json(pretty=args.pretty, preset_file=args.preset_file))
        return

    if args.command == "evaluate-policies":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        selected_profiles = (
            [PolicyProfile(profile) for profile in args.policy_profiles]
            if args.policy_profiles
            else list(PolicyProfile)
        )
        summaries, records = evaluate_policy_profiles(
            profiles,
            selected_profiles,
            policy_file=args.policy_file,
        )
        calibration_summaries = summarize_policy_calibration(
            records,
            selected_profiles=selected_profiles,
        )
        metadata = {
            "organization": args.organization,
            "profile_count": args.count,
            "seed": args.seed,
            "policy_profiles": [profile.value for profile in selected_profiles],
            "policy_file": str(Path(args.policy_file).resolve()) if args.policy_file else None,
        }
        comparison_table = (
            render_evaluation_comparison_table(summaries)
            if args.include_table or args.save_run
            else None
        )
        calibration_table = (
            render_policy_calibration_table(calibration_summaries)
            if args.include_table or args.save_run
            else None
        )
        artifacts = None
        if args.save_run:
            artifacts = write_evaluation_artifacts(
                summaries,
                records,
                output_dir=args.output_dir,
                include_records=args.include_records,
                metadata=metadata,
                calibration_summaries=calibration_summaries,
            )
        print(
            evaluation_results_to_json(
                summaries,
                records,
                calibration_summaries=calibration_summaries,
                include_records=args.include_records,
                pretty=args.pretty,
                metadata=metadata,
                comparison_table_markdown=comparison_table if args.include_table else None,
                calibration_table_markdown=calibration_table if args.include_table else None,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "compare-policies":
        baseline_profile = PolicyProfile(args.baseline_profile)
        candidate_profiles = (
            [PolicyProfile(profile) for profile in args.candidate_profiles]
            if args.candidate_profiles
            else None
        )
        selected_profiles = [baseline_profile]
        if candidate_profiles:
            selected_profiles.extend(profile for profile in candidate_profiles if profile not in selected_profiles)
        analysis_overview, rows = analyze_evaluation_runs(
            input_dir=args.input_dir,
            selected_profiles=selected_profiles if candidate_profiles else None,
        )
        comparison_overview, summaries, run_deltas = compare_policy_profiles(
            analysis_overview,
            rows,
            baseline_profile=baseline_profile,
            candidate_profiles=candidate_profiles,
        )
        comparison_table = (
            render_policy_delta_table(summaries)
            if args.include_table or args.save_comparison
            else None
        )
        artifacts = None
        if args.save_comparison:
            artifacts = write_policy_comparison_artifacts(
                comparison_overview,
                summaries,
                run_deltas,
                output_dir=args.output_dir,
            )
        print(
            comparison_results_to_json(
                comparison_overview,
                summaries,
                run_deltas,
                include_run_deltas=args.include_run_deltas,
                pretty=args.pretty,
                comparison_table_markdown=comparison_table if args.include_table else None,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "analyze-runs":
        selected_profiles = (
            [PolicyProfile(profile) for profile in args.policy_profiles]
            if args.policy_profiles
            else None
        )
        overview, rows = analyze_evaluation_runs(
            input_dir=args.input_dir,
            selected_profiles=selected_profiles,
        )
        calibration_rows = analyze_evaluation_calibration_runs(
            input_dir=args.input_dir,
            selected_profiles=selected_profiles,
        )
        comparison_table = (
            render_run_analysis_table(rows)
            if args.include_table or args.save_analysis
            else None
        )
        calibration_table = (
            render_run_calibration_table(calibration_rows)
            if args.include_table or args.save_analysis
            else None
        )
        artifacts = None
        if args.save_analysis:
            artifacts = write_run_analysis_artifacts(
                overview,
                rows,
                calibration_rows=calibration_rows,
                output_dir=args.output_dir,
            )
        print(
            analysis_results_to_json(
                overview,
                rows,
                calibration_rows=calibration_rows,
                include_rows=args.include_rows,
                pretty=args.pretty,
                comparison_table_markdown=comparison_table if args.include_table else None,
                calibration_table_markdown=calibration_table if args.include_table else None,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "generate-figures":
        selected_profiles = (
            [PolicyProfile(profile) for profile in args.policy_profiles]
            if args.policy_profiles
            else None
        )
        overview, rows = analyze_evaluation_runs(
            input_dir=args.input_dir,
            selected_profiles=selected_profiles,
        )
        aggregates = aggregate_policy_rows(rows)
        summary_table = (
            render_policy_aggregate_table(aggregates)
            if args.include_table or args.save_figures
            else None
        )
        artifacts = None
        if args.save_figures:
            artifacts = write_figure_artifacts(
                overview,
                aggregates,
                output_dir=args.output_dir,
            )
        print(
            figure_results_to_json(
                overview,
                aggregates,
                include_aggregates=args.include_aggregates,
                pretty=args.pretty,
                summary_table_markdown=summary_table if args.include_table else None,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "run-preset":
        preset = get_preset(args.preset, preset_file=args.preset_file)
        summary = execute_preset(
            preset,
            output_dir=args.output_dir,
        )
        from .presets import preset_execution_to_json  # local import keeps top import list tidy

        print(preset_execution_to_json(summary, pretty=args.pretty))
        return

    if args.command == "summarize-presets":
        (
            overview,
            run_records,
            policy_records,
            calibration_records,
            comparison_records,
        ) = summarize_preset_runs(
            input_dir=args.input_dir,
            selected_presets=args.preset_names,
        )
        preset_table = (
            render_preset_run_table(run_records)
            if args.include_tables or args.save_summary
            else None
        )
        policy_table = (
            render_preset_policy_table(policy_records)
            if args.include_tables or args.save_summary
            else None
        )
        calibration_table = (
            render_preset_calibration_table(calibration_records)
            if args.include_tables or args.save_summary
            else None
        )
        comparison_table = (
            render_preset_comparison_table(comparison_records)
            if comparison_records and (args.include_tables or args.save_summary)
            else None
        )
        artifacts = None
        if args.save_summary:
            artifacts = write_preset_results_artifacts(
                overview,
                run_records,
                policy_records,
                calibration_records,
                comparison_records,
                output_dir=args.output_dir,
            )
        print(
            preset_results_to_json(
                overview,
                run_records,
                policy_records,
                calibration_records,
                comparison_records,
                include_runs=args.include_runs,
                include_policy_summaries=args.include_policy_summaries,
                include_calibration_summaries=args.include_policy_summaries,
                include_comparison_summaries=args.include_comparison_summaries,
                pretty=args.pretty,
                preset_table_markdown=preset_table if args.include_tables else None,
                policy_table_markdown=policy_table if args.include_tables else None,
                calibration_table_markdown=(
                    calibration_table if args.include_tables else None
                ),
                comparison_table_markdown=(
                    comparison_table if args.include_tables else None
                ),
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "aggregate-presets":
        (
            results_overview,
            run_records,
            policy_records,
            calibration_records,
            comparison_records,
        ) = (
            summarize_preset_runs(
                input_dir=args.input_dir,
                selected_presets=args.preset_names,
            )
        )
        (
            aggregate_overview,
            preset_policy_records,
            preset_calibration_records,
            preset_comparison_records,
            cross_policy_records,
            cross_calibration_records,
            cross_comparison_records,
        ) = aggregate_preset_results(
            results_overview,
            run_records,
            policy_records,
            calibration_records,
            comparison_records,
        )
        artifacts = None
        if args.save_aggregates:
            artifacts = write_preset_aggregate_artifacts(
                aggregate_overview,
                preset_policy_records,
                preset_calibration_records,
                preset_comparison_records,
                cross_policy_records,
                cross_calibration_records,
                cross_comparison_records,
                output_dir=args.output_dir,
            )
        print(
            preset_aggregate_results_to_json(
                aggregate_overview,
                preset_policy_records,
                preset_calibration_records,
                preset_comparison_records,
                cross_policy_records,
                cross_calibration_records,
                cross_comparison_records,
                pretty=args.pretty,
                include_tables=args.include_tables,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "sweep-thresholds":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        overview, records = run_threshold_sweep(
            profiles,
            base_profile=PolicyProfile(args.base_profile),
            threshold_offsets=list(args.threshold_offsets),
            organization=args.organization,
            seed=args.seed,
            policy_file=args.policy_file,
        )
        artifacts = None
        if args.save_sweep:
            artifacts = write_threshold_sweep_artifacts(
                overview,
                records,
                output_dir=args.output_dir,
            )
        print(
            threshold_sweep_results_to_json(
                overview,
                records,
                include_table=args.include_table,
                pretty=args.pretty,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "analyze-threshold-sweeps":
        selected_profiles = (
            [PolicyProfile(profile) for profile in args.base_profiles]
            if args.base_profiles
            else None
        )
        overview, rows, aggregates = analyze_threshold_sweeps(
            input_dir=args.input_dir,
            selected_base_profiles=selected_profiles,
        )
        run_table = (
            render_threshold_sweep_run_table(rows)
            if args.include_tables or args.save_analysis
            else None
        )
        aggregate_table = (
            render_threshold_sweep_aggregate_table(aggregates)
            if args.include_tables or args.save_analysis
            else None
        )
        artifacts = None
        if args.save_analysis:
            artifacts = write_threshold_sweep_analysis_artifacts(
                overview,
                rows,
                aggregates,
                output_dir=args.output_dir,
            )
        print(
            threshold_sweep_analysis_to_json(
                overview,
                rows,
                aggregates,
                include_rows=args.include_rows,
                include_aggregates=args.include_aggregates,
                pretty=args.pretty,
                run_table_markdown=run_table if args.include_tables else None,
                aggregate_table_markdown=aggregate_table if args.include_tables else None,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "generate-threshold-sweep-figures":
        selected_profiles = (
            [PolicyProfile(profile) for profile in args.base_profiles]
            if args.base_profiles
            else None
        )
        overview, _, aggregates = analyze_threshold_sweeps(
            input_dir=args.input_dir,
            selected_base_profiles=selected_profiles,
        )
        summary_table = (
            render_threshold_sweep_aggregate_table(aggregates)
            if args.include_table or args.save_figures
            else None
        )
        artifacts = None
        if args.save_figures:
            artifacts = write_threshold_sweep_figure_artifacts(
                overview,
                aggregates,
                output_dir=args.output_dir,
                summary_table_markdown=summary_table,
            )
        print(
            threshold_sweep_figure_results_to_json(
                overview,
                aggregates,
                include_aggregates=args.include_aggregates,
                pretty=args.pretty,
                summary_table_markdown=summary_table if args.include_table else None,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "train-model":
        if args.input_file:
            import csv as _csv

            with open(args.input_file, newline="", encoding="utf-8") as fh:
                rows = list(_csv.DictReader(fh))
            from .dataset import _csv_rows_to_records

            records = _csv_rows_to_records(rows)
        else:
            profiles = generate_synthetic_profiles(
                count=args.count,
                organization=args.organization,
                seed=args.seed,
            )
            _, records = generate_dataset(
                profiles,
                policy_profile=PolicyProfile(args.policy_profile),
                organization=args.organization,
                seed=args.seed,
            )
        if args.folds:
            cv_result = train_model_cv(
                records,
                n_folds=args.folds,
                model_type=args.model_type,
                random_state=args.random_state,
            )
            payload = cv_result.to_dict()
            if args.pretty:
                print(json.dumps(payload, indent=2))
            else:
                print(json.dumps(payload))
            return

        result, fitted_model = train_model(
            records,
            model_type=args.model_type,
            test_size=args.test_size,
            random_state=args.random_state,
        )
        artifacts = None
        if args.save_model:
            artifacts = save_model(fitted_model, result, output_dir=args.output_dir)
        print(
            training_results_to_json(
                result,
                pretty=args.pretty,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "generate-dataset":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        overview, records = generate_dataset(
            profiles,
            policy_profile=PolicyProfile(args.policy_profile),
            organization=args.organization,
            seed=args.seed,
            policy_file=args.policy_file,
        )
        artifacts = None
        if args.save_dataset:
            artifacts = write_dataset_artifacts(
                overview,
                records,
                output_dir=args.output_dir,
            )
        print(
            dataset_results_to_json(
                overview,
                records,
                include_records=args.include_records,
                pretty=args.pretty,
                artifacts=artifacts.to_dict() if artifacts else None,
            )
        )
        return

    if args.command == "explain-recommendation":
        profiles = generate_synthetic_profiles(
            count=args.count,
            organization=args.organization,
            seed=args.seed,
        )
        if args.profile_index < 0 or args.profile_index >= len(profiles):
            parser.error("--profile-index must refer to a generated synthetic profile")

        profile = profiles[args.profile_index]
        exposure = score_profiles_exposure([profile])[0]
        password_assessment = score_password_for_profile(args.password, profile)
        config = get_policy_config(args.policy_profile, policy_file=args.policy_file)

        predicted_band = None
        if args.model_file:
            from .exposure import profile_to_attribute_vector
            from .model import load_model_artifacts, predict_risk_band as _predict

            vector = profile_to_attribute_vector(profile)
            fitted_model, _ = load_model_artifacts(args.model_file)
            predicted_band = _predict(fitted_model, vector, password_assessment)

        recommendation = recommend_hardening(
            exposure,
            password_assessment,
            config=config,
            predicted_password_band=predicted_band,
        )
        explanation = explain_recommendation(recommendation, profile, exposure, password_assessment)
        print(explanation_to_json(explanation, pretty=args.pretty))
        return

    if args.command == "list-sweep-presets":
        print(sweep_presets_to_json(pretty=args.pretty, preset_file=args.sweep_preset_file))
        return

    if args.command == "run-sweep-preset":
        preset = get_sweep_preset(args.preset, preset_file=args.sweep_preset_file)
        summary = execute_sweep_preset(
            preset,
            output_dir=args.output_dir,
        )
        print(sweep_preset_execution_to_json(summary, pretty=args.pretty))
        return

    if args.command == "serve":
        try:
            import uvicorn  # type: ignore[import-not-found]
        except ImportError as exc:
            parser.error(
                "uvicorn is required for the serve command. "
                "Install it with: pip install signallock[api]"
            )
            raise SystemExit(2) from exc

        from .api import create_app

        app = create_app(model_file=args.model_file, cors_origins=args.cors_origins)
        print(
            f"SignalLock API listening on http://{args.host}:{args.port}  "
            f"(model_loaded={args.model_file is not None})"
        )
        uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
        return

    print("SignalLock is a defensive research prototype for context-aware authentication hardening.")
    print("Use --help to browse commands, or start with a synthetic evaluation run.")
    print(
        "Try: PYTHONPATH=src .venv/bin/python -m signallock "
        "evaluate-policies --count 5 --seed 1 --pretty"
    )
