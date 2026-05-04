"""CLI entrypoint for the SignalLock project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import (
    analysis_results_to_json,
    analyze_evaluation_runs,
    render_run_analysis_table,
    write_run_analysis_artifacts,
)
from .comparison import (
    compare_policy_profiles,
    comparison_results_to_json,
    render_policy_comparison_table as render_policy_delta_table,
    write_policy_comparison_artifacts,
)
from .evaluation import evaluate_policy_profiles, evaluation_results_to_json
from .exposure import assessments_to_json, score_profiles_exposure
from .figures import (
    aggregate_policy_rows,
    figure_results_to_json,
    render_policy_aggregate_table,
    write_figure_artifacts,
)
from .password_risk import score_password_for_profile
from .policy import get_policy_config, policy_configs_to_json, recommend_hardening
from .presets import execute_preset, get_preset, presets_to_json
from .reporting import (
    DEFAULT_EVALUATION_OUTPUT_DIR,
    render_policy_comparison_table as render_evaluation_comparison_table,
    write_evaluation_artifacts,
)
from .schemas import PolicyProfile
from .synthetic_profiles import generate_synthetic_profiles, profiles_to_json


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
        recommendation = recommend_hardening(exposure, password_assessment, config=config)
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
        artifacts = None
        if args.save_run:
            artifacts = write_evaluation_artifacts(
                summaries,
                records,
                output_dir=args.output_dir,
                include_records=args.include_records,
                metadata=metadata,
            )
        print(
            evaluation_results_to_json(
                summaries,
                records,
                include_records=args.include_records,
                pretty=args.pretty,
                metadata=metadata,
                comparison_table_markdown=comparison_table if args.include_table else None,
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
        comparison_table = (
            render_run_analysis_table(rows)
            if args.include_table or args.save_analysis
            else None
        )
        artifacts = None
        if args.save_analysis:
            artifacts = write_run_analysis_artifacts(
                overview,
                rows,
                output_dir=args.output_dir,
            )
        print(
            analysis_results_to_json(
                overview,
                rows,
                include_rows=args.include_rows,
                pretty=args.pretty,
                comparison_table_markdown=comparison_table if args.include_table else None,
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

    print("SignalLock is in early implementation.")
    print("Start with docs/THREAT_MODEL.md, docs/FEATURE_SCHEMA.md, and the CLI help.")
    print(
        "Try: PYTHONPATH=src python3 -m signallock "
        "evaluate-policies --count 5 --seed 1 --pretty"
    )
