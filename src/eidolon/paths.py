"""Project-root and runtime path helpers for Eidolon."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _looks_like_project_root(path: Path) -> bool:
    """Return True when the path looks like a Eidolon checkout/runtime root."""
    return (path / "configs").is_dir() and (
        (path / "src" / "eidolon").is_dir() or (path / "artifacts").exists()
    )


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Resolve the project root across source, installed, and container contexts."""
    env_root = os.environ.get("EIDOLON_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    package_path = Path(__file__).resolve()
    source_candidate = package_path.parents[2]
    cwd_candidate = Path.cwd().resolve()

    for candidate in (source_candidate, cwd_candidate):
        if _looks_like_project_root(candidate):
            return candidate

    for candidate in (cwd_candidate, source_candidate):
        if (candidate / "configs").is_dir():
            return candidate

    return cwd_candidate


def config_path(filename: str) -> Path:
    """Return the path to a config JSON file under the project root."""
    return get_project_root() / "configs" / filename


def artifacts_path(*parts: str) -> Path:
    """Return the path to an artifacts subdirectory under the project root."""
    return get_project_root() / "artifacts" / Path(*parts)
