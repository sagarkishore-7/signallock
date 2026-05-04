"""CLI entrypoint for the SignalLock project."""

from __future__ import annotations

import argparse
import json

from .evaluation import evaluate_policy_profiles, evaluation_results_to_json
from .exposure import assessments_to_json, score_profiles_exposure
from .password_risk import score_password_for_profile
from .policy import get_policy_config, policy_configs_to_json, recommend_hardening
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
        print(
            evaluation_results_to_json(
                summaries,
                records,
                include_records=args.include_records,
                pretty=args.pretty,
            )
        )
        return

    print("SignalLock is in early implementation.")
    print("Start with docs/THREAT_MODEL.md, docs/FEATURE_SCHEMA.md, and the CLI help.")
    print(
        "Try: PYTHONPATH=src python3 -m signallock "
        "evaluate-policies --count 5 --seed 1 --pretty"
    )
