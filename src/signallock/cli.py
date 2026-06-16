"""Command-line interface for SignalLock v2.

Subcommands mirror the pipeline:

    collect           resolve a consented subject from its snapshot
    collect-live      run live (GitHub) collection -> consented snapshot
    score             exposure (+ optional predictability/recommendation)
    compare-baseline  contextual band vs zxcvbn + exposure premium
    build-dataset     run the pipeline over the roster -> labeled CSV/JSON
    evaluate          train + evaluate the learned model, premium, ablations
    mirror-table      print the adversary-mirror registry
    serve             run the FastAPI service (for the dashboard)
    demo              run the optional localhost attack/defense showcase
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from .collect.base import adversary_mirror_table
from .collect.code_profile import CodeProfile
from .collect.snapshot import load_snapshot
from .core.enums import Visibility
from .core.errors import CollectorError, ConsentError
from .core.evidence import Observation
from .core.identity import ConsentedIdentity, ConsentRoster, IdentitySeeds
from .eval.dataset import (
    build_dataset,
    load_observations_dir,
)
from .eval.metrics import ablation_study, evaluate_dataset
from .exposure.model import assess_exposure
from .paths import get_project_root
from .policy.engine import recommend
from .predict.baseline import context_free_strength
from .predict.premium import exposure_premium
from .predict.simulator import simulate_predictability
from .resolve.entity import filter_by_visibility, resolve_subject

#: --visibility choice -> the maximum accessibility tier to score.
_VISIBILITY = {
    "public": Visibility.PUBLIC,
    "gated": Visibility.GATED,
    "all": Visibility.PRIVATE,
}


def _configs() -> Path:
    return get_project_root() / "configs"


def _default(name: str) -> Path:
    return _configs() / name


def _artifacts(*parts: str) -> Path:
    return get_project_root() / "artifacts" / Path(*parts)


def _load_roster(path: str | None) -> ConsentRoster:
    roster_path = Path(path) if path else _default("osint_roster.example.json")
    return ConsentRoster.load(roster_path)


def _identity(subject_id: str, roster: ConsentRoster) -> ConsentedIdentity:
    return ConsentedIdentity(
        subject_id=subject_id,
        seeds=IdentitySeeds(username=subject_id),
        consent=roster.get(subject_id),  # type: ignore[arg-type]
    )


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def _load_observations(args: argparse.Namespace) -> dict[str, list[Observation]]:
    """Load snapshots, filtered to the requested ``--visibility`` tier (if any)."""
    observations = load_observations_dir(args.snapshots or _default("snapshots"))
    tier = _VISIBILITY.get(getattr(args, "visibility", None) or "all", Visibility.PRIVATE)
    if tier is Visibility.PRIVATE:
        return observations
    return {
        subject_id: filter_by_visibility(obs, tier)
        for subject_id, obs in observations.items()
    }


# --------------------------------------------------------------------------- #
# commands


def cmd_collect(args: argparse.Namespace) -> int:
    roster = _load_roster(args.roster)
    observations = _load_observations(args)
    if args.subject not in observations:
        print(f"no snapshot found for subject '{args.subject}'", file=sys.stderr)
        return 2
    subject = resolve_subject(args.subject, observations[args.subject])
    exposure = assess_exposure(subject)
    _print({"subject": subject.to_dict(), "exposure": exposure.to_dict()})
    return 0


def collect_live_observations(
    subject_id: str,
    github_user: str,
    roster: ConsentRoster,
    *,
    client=None,
    token: str | None = None,
) -> list[Observation]:
    """Run the live, ToS-permitted collectors for a consented subject.

    Currently wires the GitHub :class:`CodeProfile` collector — the one source
    with a real public-API path. Consent is enforced inside ``Collector.collect``
    (and re-checked here so a non-roster subject fails fast with a clear message).
    ``client`` is an injectable httpx-style client for offline tests.
    """
    record = roster.get(subject_id)
    if record is None:
        raise ConsentError(
            f"No consent on record for subject '{subject_id}'. "
            "Add it to the roster before collecting."
        )
    identity = ConsentedIdentity(
        subject_id=subject_id,
        seeds=IdentitySeeds(username=github_user),
        consent=record,
    )
    return CodeProfile(client=client, token=token).collect(identity, roster=roster)


def _merge_observations(
    existing: list[Observation], new: list[Observation]
) -> list[Observation]:
    """Union observations, de-duping on (source, attr_kind, lowercased value)."""
    merged: list[Observation] = []
    seen: set[tuple[str, str, str]] = set()
    for obs in list(existing) + list(new):
        key = (obs.source.value, obs.attr_kind.value, obs.value.lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append(obs)
    return merged


def _write_snapshot(
    path: Path, subject_id: str, observations: list[Observation]
) -> None:
    """Serialize observations into the snapshot schema ``load_snapshot`` reads."""
    payload = {
        "subject_id": subject_id,
        "observations": [
            {k: v for k, v in obs.to_dict().items() if k != "subject_id"}
            for obs in observations
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def cmd_collect_live(args: argparse.Namespace) -> int:
    roster = _load_roster(args.roster)
    if args.subject not in roster:
        print(
            f"subject '{args.subject}' is not in the roster — add a consent "
            "record first",
            file=sys.stderr,
        )
        return 2

    snap_dir = Path(args.snapshots) if args.snapshots else _default("snapshots")
    out_path = Path(args.out) if args.out else snap_dir / f"{args.subject}.json"
    existing = load_snapshot(out_path) if out_path.exists() else []
    if existing and not args.merge:
        print(
            f"snapshot {out_path} already exists; pass --merge to add to it "
            "(keeps your hand-authored social/professional observations)",
            file=sys.stderr,
        )
        return 2

    try:
        live = collect_live_observations(
            args.subject,
            args.github_user,
            roster,
            token=os.environ.get("GITHUB_TOKEN"),
        )
    except CollectorError as exc:
        print(f"live collection failed: {exc}", file=sys.stderr)
        return 1

    merged = _merge_observations(existing, live) if args.merge else live
    _write_snapshot(out_path, args.subject, merged)
    print(
        f"collected {len(live)} live observations from github:{args.github_user}; "
        f"wrote {len(merged)} total to {out_path}"
    )
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    roster = _load_roster(args.roster)
    observations = _load_observations(args)
    if args.subject not in observations:
        print(f"no snapshot found for subject '{args.subject}'", file=sys.stderr)
        return 2
    subject = resolve_subject(args.subject, observations[args.subject])
    exposure = assess_exposure(subject)
    out: dict[str, object] = {"exposure": exposure.to_dict()}
    if args.password:
        prediction = simulate_predictability(
            subject, args.password,
            identity=_identity(args.subject, roster), roster=roster,
        )
        out["predictability"] = prediction.to_dict()
        out["recommendation"] = recommend(exposure, prediction).to_dict()
    _print(out)
    return 0


def cmd_compare_baseline(args: argparse.Namespace) -> int:
    roster = _load_roster(args.roster)
    observations = _load_observations(args)
    if args.subject not in observations:
        print(f"no snapshot found for subject '{args.subject}'", file=sys.stderr)
        return 2
    subject = resolve_subject(args.subject, observations[args.subject])
    prediction = simulate_predictability(
        subject, args.password,
        identity=_identity(args.subject, roster), roster=roster,
    )
    baseline = context_free_strength(args.password)
    premium = exposure_premium(baseline, prediction)
    _print(
        {
            "subject_id": args.subject,
            "contextual_band": prediction.band.value,
            "matched_category": prediction.matched_category,
            "baseline": baseline.to_dict(),
            "premium": premium.to_dict(),
        }
    )
    return 0


def _build(args: argparse.Namespace):
    roster = _load_roster(args.roster)
    observations = _load_observations(args)
    passwords_path = Path(args.passwords) if args.passwords else _default(
        "example_passwords.example.json"
    )
    passwords = json.loads(passwords_path.read_text(encoding="utf-8"))
    return build_dataset(observations, passwords, roster), observations, roster


def cmd_build_dataset(args: argparse.Namespace) -> int:
    dataset, _, _ = _build(args)
    out_dir = Path(args.out) if args.out else _artifacts("datasets")
    out_dir.mkdir(parents=True, exist_ok=True)
    records = dataset.to_records()
    (out_dir / "dataset.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    if records:
        with (out_dir / "dataset.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    print(f"wrote {len(records)} rows to {out_dir}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    dataset, observations, roster = _build(args)
    report = evaluate_dataset(dataset, seed=args.seed)
    report["ablation"] = ablation_study(observations, roster)
    out_dir = Path(args.out) if args.out else _artifacts("evaluation")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.figures:
        try:
            from .eval.figures import save_figures

            written = save_figures(dataset, report, out_dir / "figures")
            report["figures"] = written
        except Exception as exc:  # pragma: no cover - optional dependency
            print(f"figures skipped: {exc}", file=sys.stderr)
    _print(report)
    return 0


def cmd_mirror_table(_: argparse.Namespace) -> int:
    _print(adversary_mirror_table())
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print(
            "serve requires the 'api' extra: pip install 'signallock[api]'",
            file=sys.stderr,
        )
        return 2
    from .api import create_app

    roster = (
        Path(args.roster) if args.roster else _default("osint_roster.example.json")
    )
    snapshots = Path(args.snapshots) if args.snapshots else _default("snapshots")
    origins = [
        o.strip() for o in (args.cors_origins or "").split(",") if o.strip()
    ] or None
    app = create_app(roster_path=roster, snapshots_dir=snapshots, cors_origins=origins)
    print(
        f"serving SignalLock API on http://{args.host}:{args.port} "
        f"(roster={roster.name}, cors={origins or 'none'})"
    )
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    try:
        sys.path.insert(0, str(get_project_root()))
        from demo.run_defense import run_defense  # type: ignore
        from demo.target_service import create_app  # type: ignore
    except Exception as exc:
        print(
            "demo package not importable (run from the repo root, install "
            f"'[demo]' extra): {exc}",
            file=sys.stderr,
        )
        return 2
    roster = _load_roster(args.roster)
    observations = _load_observations(args)
    if args.subject not in observations:
        print(f"no snapshot found for subject '{args.subject}'", file=sys.stderr)
        return 2
    subject = resolve_subject(args.subject, observations[args.subject])
    app = create_app(args.password)
    result = run_defense(
        app=app,
        subject=subject,
        seed_password=args.password,
        limit=args.limit,
        identity=_identity(args.subject, roster),
        roster=roster,
    )
    _print(result)
    return 0


# --------------------------------------------------------------------------- #
# parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="signallock", description=__doc__)
    parser.add_argument("--roster", help="path to a consent roster JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--snapshots", help="snapshots directory")

    def add_visibility(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--visibility",
            choices=["public", "gated", "all"],
            default="all",
            help="accessibility tier to score: public-only, +connection-gated, or all",
        )

    p_collect = sub.add_parser("collect", help="resolve a subject from its snapshot")
    p_collect.add_argument("--subject", required=True)
    add_common(p_collect)
    add_visibility(p_collect)
    p_collect.set_defaults(func=cmd_collect)

    p_live = sub.add_parser(
        "collect-live", help="run live (GitHub) collection -> consented snapshot"
    )
    p_live.add_argument("--subject", required=True)
    p_live.add_argument(
        "--github-user", required=True, help="real GitHub username seed to collect"
    )
    p_live.add_argument(
        "--out", help="snapshot output path (default <snapshots>/<subject>.json)"
    )
    p_live.add_argument(
        "--merge",
        action="store_true",
        help="merge into an existing snapshot instead of refusing to overwrite",
    )
    add_common(p_live)
    p_live.set_defaults(func=cmd_collect_live)

    p_score = sub.add_parser("score", help="exposure (+ optional predictability)")
    p_score.add_argument("--subject", required=True)
    p_score.add_argument("--password")
    add_common(p_score)
    add_visibility(p_score)
    p_score.set_defaults(func=cmd_score)

    p_cmp = sub.add_parser("compare-baseline", help="contextual vs zxcvbn + premium")
    p_cmp.add_argument("--subject", required=True)
    p_cmp.add_argument("--password", required=True)
    add_common(p_cmp)
    add_visibility(p_cmp)
    p_cmp.set_defaults(func=cmd_compare_baseline)

    p_ds = sub.add_parser("build-dataset", help="build the labeled dataset")
    add_common(p_ds)
    add_visibility(p_ds)
    p_ds.add_argument("--passwords", help="passwords map JSON")
    p_ds.add_argument("--out", help="output directory")
    p_ds.set_defaults(func=cmd_build_dataset)

    p_eval = sub.add_parser("evaluate", help="train + evaluate the learned model")
    add_common(p_eval)
    add_visibility(p_eval)
    p_eval.add_argument("--passwords", help="passwords map JSON")
    p_eval.add_argument("--out", help="output directory")
    p_eval.add_argument("--seed", type=int, default=7)
    p_eval.add_argument("--figures", action="store_true")
    p_eval.set_defaults(func=cmd_evaluate)

    p_mirror = sub.add_parser("mirror-table", help="print the adversary-mirror table")
    p_mirror.set_defaults(func=cmd_mirror_table)

    p_serve = sub.add_parser("serve", help="run the FastAPI service (needs api extra)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument(
        "--cors-origins",
        help="comma-separated CORS origins, e.g. http://localhost:3000",
    )
    add_common(p_serve)
    p_serve.set_defaults(func=cmd_serve)

    p_demo = sub.add_parser("demo", help="run the localhost attack/defense showcase")
    p_demo.add_argument("--subject", required=True)
    p_demo.add_argument("--password", required=True, help="the weak seed password")
    p_demo.add_argument("--limit", type=int, default=500, help="guess budget")
    add_common(p_demo)
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
