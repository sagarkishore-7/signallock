"""Preset-based orchestration for multi-seed threshold-sweep experiment suites."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .paths import artifacts_path, config_path
from .reporting import normalize_artifact_path
from .schemas import (
    PolicyProfile,
    SweepPresetArtifacts,
    SweepPresetExecutionSummary,
    ThresholdSweepPreset,
)
from .synthetic_profiles import generate_synthetic_profiles
from .threshold_sweep_analysis import (
    analyze_threshold_sweeps,
    render_threshold_sweep_aggregate_table,
    write_threshold_sweep_analysis_artifacts,
)
from .threshold_sweep_figures import write_threshold_sweep_figure_artifacts
from .threshold_sweeps import run_threshold_sweep, write_threshold_sweep_artifacts


DEFAULT_SWEEP_PRESET_FILE = config_path("threshold_sweep_presets.json")
DEFAULT_SWEEP_PRESET_OUTPUT_DIR = artifacts_path("sweep_presets")


def load_sweep_presets(preset_file: str | Path | None = None) -> list[ThresholdSweepPreset]:
    """Load threshold-sweep preset definitions from JSON."""
    path = Path(preset_file) if preset_file else DEFAULT_SWEEP_PRESET_FILE
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [_preset_from_dict(item) for item in payload.get("sweep_presets", [])]


def get_sweep_preset(
    name: str,
    preset_file: str | Path | None = None,
) -> ThresholdSweepPreset:
    """Return a named threshold-sweep preset from the configured preset file."""
    for preset in load_sweep_presets(preset_file=preset_file):
        if preset.name == name:
            return preset
    raise KeyError(f"unknown sweep preset: {name}")


def sweep_presets_to_json(
    pretty: bool = False,
    preset_file: str | Path | None = None,
) -> str:
    """Serialize threshold-sweep preset definitions as JSON."""
    payload = [preset.to_dict() for preset in load_sweep_presets(preset_file=preset_file)]
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def execute_sweep_preset(
    preset: ThresholdSweepPreset,
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> SweepPresetExecutionSummary:
    """Execute one threshold-sweep preset end to end and save a manifest bundle."""
    generated_at = generated_at or datetime.now(timezone.utc)
    root_dir = normalize_artifact_path(output_dir, DEFAULT_SWEEP_PRESET_OUTPUT_DIR)
    base_run_id = f"{generated_at.strftime('%Y%m%dT%H%M%SZ')}-{_safe_name(preset.name)}"
    run_dir, resolved_run_id = _create_unique_run_directory(root_dir, base_run_id)

    sweeps_dir = run_dir / "sweeps"
    analysis_dir = run_dir / "analysis"
    figures_dir = run_dir / "figures"
    sweeps_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    sweep_artifact_list: list[dict[str, object]] = []
    index = 0

    for seed in preset.seeds:
        profiles = generate_synthetic_profiles(
            count=preset.profile_count,
            organization=preset.organization,
            seed=seed,
        )
        for base_profile in preset.base_profiles:
            overview, records = run_threshold_sweep(
                profiles,
                base_profile=base_profile,
                threshold_offsets=list(preset.threshold_offsets),
                organization=preset.organization,
                seed=seed,
            )
            sweep = write_threshold_sweep_artifacts(
                overview,
                records,
                output_dir=sweeps_dir,
                generated_at=generated_at + timedelta(seconds=index),
            )
            sweep_artifact_list.append(sweep.to_dict())
            index += 1

    analysis_overview, rows, aggregates = analyze_threshold_sweeps(
        input_dir=sweeps_dir,
        selected_base_profiles=list(preset.base_profiles),
    )
    analysis = write_threshold_sweep_analysis_artifacts(
        analysis_overview,
        rows,
        aggregates,
        output_dir=analysis_dir,
        generated_at=generated_at + timedelta(minutes=10),
    )

    summary_table = render_threshold_sweep_aggregate_table(aggregates)
    figures = write_threshold_sweep_figure_artifacts(
        analysis_overview,
        aggregates,
        output_dir=figures_dir,
        generated_at=generated_at + timedelta(minutes=20),
        summary_table_markdown=summary_table,
    )

    preset_artifacts = SweepPresetArtifacts(
        run_id=resolved_run_id,
        generated_at=generated_at.isoformat(),
        output_dir=str(run_dir.resolve()),
        sweeps_dir=str(sweeps_dir.resolve()),
        analysis_dir=str(analysis_dir.resolve()),
        figures_dir=str(figures_dir.resolve()),
        manifest_file=str((run_dir / "sweep_preset_manifest.json").resolve()),
    )

    execution = SweepPresetExecutionSummary(
        preset_name=preset.name,
        description=preset.description,
        organization=preset.organization,
        profile_count=preset.profile_count,
        seeds=list(preset.seeds),
        base_profiles=list(preset.base_profiles),
        threshold_offsets=list(preset.threshold_offsets),
        generated_at=generated_at.isoformat(),
        sweep_run_count=len(sweep_artifact_list),
        sweep_artifacts=sweep_artifact_list,
        analysis_artifacts=analysis.to_dict(),
        figure_artifacts=figures.to_dict(),
        preset_artifacts=preset_artifacts.to_dict(),
    )

    Path(preset_artifacts.manifest_file).write_text(
        json.dumps(execution.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return execution


def sweep_preset_execution_to_json(
    summary: SweepPresetExecutionSummary,
    pretty: bool = False,
) -> str:
    """Serialize an executed sweep preset summary as JSON."""
    payload = summary.to_dict()
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)


def _preset_from_dict(data: dict[str, object]) -> ThresholdSweepPreset:
    """Convert raw JSON into a ThresholdSweepPreset instance."""
    return ThresholdSweepPreset(
        name=str(data["name"]),
        description=str(data["description"]),
        organization=str(data["organization"]),
        profile_count=int(data["profile_count"]),
        seeds=[int(seed) for seed in data["seeds"]],
        base_profiles=[PolicyProfile(profile) for profile in data["base_profiles"]],
        threshold_offsets=[float(offset) for offset in data["threshold_offsets"]],
    )


def _create_unique_run_directory(root_dir: Path, base_run_id: str) -> tuple[Path, str]:
    """Create a timestamped sweep-preset directory, avoiding collisions within the same second."""
    root_dir.mkdir(parents=True, exist_ok=True)
    for index in range(0, 1000):
        run_id = base_run_id if index == 0 else f"{base_run_id}-{index:02d}"
        run_dir = root_dir / run_id
        if not run_dir.exists():
            run_dir.mkdir()
            return run_dir, run_id
    raise RuntimeError("unable to allocate a unique sweep-preset directory")


def _safe_name(value: str) -> str:
    """Convert a preset name into a filesystem-safe token."""
    cleaned = "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")
    return cleaned or "sweep"
