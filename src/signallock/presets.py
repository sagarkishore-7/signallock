"""Preset-based orchestration for reproducible SignalLock experiment suites."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .paths import artifacts_path, config_path
from .analysis import (
    analyze_evaluation_calibration_runs,
    analyze_evaluation_runs,
    write_run_analysis_artifacts,
)
from .comparison import compare_policy_profiles, write_policy_comparison_artifacts
from .evaluation import evaluate_policy_profiles
from .figures import aggregate_policy_rows, write_figure_artifacts
from .reporting import normalize_artifact_path, write_evaluation_artifacts
from .schemas import (
    ExperimentPreset,
    PolicyProfile,
    PresetArtifacts,
    PresetExecutionSummary,
)
from .synthetic_profiles import generate_synthetic_profiles


DEFAULT_PRESET_FILE = config_path("experiment_presets.json")
DEFAULT_PRESET_OUTPUT_DIR = artifacts_path("presets")


def load_presets(preset_file: str | Path | None = None) -> list[ExperimentPreset]:
    """Load preset definitions from JSON."""
    path = Path(preset_file) if preset_file else DEFAULT_PRESET_FILE
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [_preset_from_dict(item) for item in payload.get("presets", [])]


def get_preset(name: str, preset_file: str | Path | None = None) -> ExperimentPreset:
    """Return a named preset from the configured preset file."""
    for preset in load_presets(preset_file=preset_file):
        if preset.name == name:
            return preset
    raise KeyError(f"unknown preset: {name}")


def presets_to_json(pretty: bool = False, preset_file: str | Path | None = None) -> str:
    """Serialize preset definitions as JSON."""
    payload = [preset.to_dict() for preset in load_presets(preset_file=preset_file)]
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def execute_preset(
    preset: ExperimentPreset,
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> PresetExecutionSummary:
    """Execute one preset end to end and save a manifest bundle."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_PRESET_OUTPUT_DIR)
    base_run_id = f"{generated_at.strftime('%Y%m%dT%H%M%SZ')}-{_safe_name(preset.name)}"
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, base_run_id)

    evaluations_dir = run_dir / "evaluations"
    analysis_dir = run_dir / "analysis"
    comparisons_dir = run_dir / "comparisons"
    figures_dir = run_dir / "figures"
    evaluations_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    comparisons_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    evaluation_artifacts: list[dict[str, object]] = []
    selected_profiles = list(preset.policy_profiles)

    for index, seed in enumerate(preset.seeds):
        profiles = generate_synthetic_profiles(
            count=preset.profile_count,
            organization=preset.organization,
            seed=seed,
        )
        summaries, records = evaluate_policy_profiles(profiles, selected_profiles)
        evaluation = write_evaluation_artifacts(
            summaries,
            records,
            output_dir=evaluations_dir,
            include_records=preset.include_records,
            metadata={
                "organization": preset.organization,
                "profile_count": preset.profile_count,
                "seed": seed,
                "policy_profiles": [profile.value for profile in selected_profiles],
                "preset_name": preset.name,
            },
            generated_at=generated_at + timedelta(seconds=index),
        )
        evaluation_artifacts.append(evaluation.to_dict())

    analysis_overview, rows = analyze_evaluation_runs(
        input_dir=evaluations_dir,
        selected_profiles=selected_profiles,
    )
    calibration_rows = analyze_evaluation_calibration_runs(
        input_dir=evaluations_dir,
        selected_profiles=selected_profiles,
    )
    analysis = write_run_analysis_artifacts(
        analysis_overview,
        rows,
        calibration_rows=calibration_rows,
        output_dir=analysis_dir,
        generated_at=generated_at + timedelta(minutes=10),
    )

    comparison_artifacts: dict[str, object] | None = None
    if preset.comparison_candidates:
        comparison_overview, summaries, run_deltas = compare_policy_profiles(
            analysis_overview,
            rows,
            baseline_profile=preset.baseline_profile,
            candidate_profiles=list(preset.comparison_candidates),
        )
        comparison = write_policy_comparison_artifacts(
            comparison_overview,
            summaries,
            run_deltas,
            output_dir=comparisons_dir,
            generated_at=generated_at + timedelta(minutes=20),
        )
        comparison_artifacts = comparison.to_dict()

    aggregates = aggregate_policy_rows(rows)
    figures = write_figure_artifacts(
        analysis_overview,
        aggregates,
        output_dir=figures_dir,
        generated_at=generated_at + timedelta(minutes=30),
    )

    preset_artifacts = PresetArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        evaluations_dir=str(evaluations_dir.resolve()),
        analysis_dir=str(analysis_dir.resolve()),
        comparisons_dir=str(comparisons_dir.resolve()),
        figures_dir=str(figures_dir.resolve()),
        manifest_file=str((run_dir / "preset_manifest.json").resolve()),
    )

    execution = PresetExecutionSummary(
        preset_name=preset.name,
        description=preset.description,
        organization=preset.organization,
        profile_count=preset.profile_count,
        seeds=list(preset.seeds),
        policy_profiles=list(preset.policy_profiles),
        baseline_profile=preset.baseline_profile,
        comparison_candidates=list(preset.comparison_candidates),
        include_records=preset.include_records,
        generated_at=generated_at.isoformat(),
        evaluation_run_count=len(evaluation_artifacts),
        evaluation_artifacts=evaluation_artifacts,
        analysis_artifacts=analysis.to_dict(),
        comparison_artifacts=comparison_artifacts,
        figure_artifacts=figures.to_dict(),
        preset_artifacts=preset_artifacts.to_dict(),
    )

    Path(preset_artifacts.manifest_file).write_text(
        json.dumps(execution.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return execution


def preset_execution_to_json(summary: PresetExecutionSummary, pretty: bool = False) -> str:
    """Serialize an executed preset summary as JSON."""
    payload = summary.to_dict()
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _preset_from_dict(data: dict[str, object]) -> ExperimentPreset:
    """Convert raw JSON into an ExperimentPreset instance."""
    return ExperimentPreset(
        name=str(data["name"]),
        description=str(data["description"]),
        organization=str(data["organization"]),
        profile_count=int(data["profile_count"]),
        seeds=[int(seed) for seed in data["seeds"]],
        policy_profiles=[PolicyProfile(profile) for profile in data["policy_profiles"]],
        baseline_profile=PolicyProfile(data["baseline_profile"]),
        comparison_candidates=[
            PolicyProfile(profile)
            for profile in data.get("comparison_candidates", [])
        ],
        include_records=bool(data.get("include_records", False)),
    )


def _create_unique_run_directory(root_dir: Path, base_run_id: str) -> tuple[Path, str]:
    """Create a timestamped preset directory, avoiding collisions within the same second."""
    root_dir.mkdir(parents=True, exist_ok=True)
    for index in range(0, 1000):
        run_id = base_run_id if index == 0 else f"{base_run_id}-{index:02d}"
        run_dir = root_dir / run_id
        if not run_dir.exists():
            run_dir.mkdir()
            return run_dir, run_id
    raise RuntimeError("unable to allocate a unique preset directory")


def _safe_name(value: str) -> str:
    """Convert a preset name into a filesystem-safe token."""
    cleaned = "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")
    return cleaned or "preset"
