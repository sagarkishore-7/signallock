"""Runtime path resolution tests for installed and container-like contexts."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from signallock.paths import config_path, get_project_root
from signallock.policy import load_policy_configs
from signallock.presets import load_presets


class PathResolutionTests(unittest.TestCase):
    """Validate that config discovery works outside the repo cwd."""

    def setUp(self) -> None:
        self.original_cwd = Path.cwd()
        self.original_project_root = os.environ.get("SIGNALLOCK_PROJECT_ROOT")
        self.repo_root = Path(__file__).resolve().parents[1]

    def tearDown(self) -> None:
        os.chdir(self.original_cwd)
        if self.original_project_root is None:
            os.environ.pop("SIGNALLOCK_PROJECT_ROOT", None)
        else:
            os.environ["SIGNALLOCK_PROJECT_ROOT"] = self.original_project_root
        get_project_root.cache_clear()

    def test_project_root_env_allows_loading_configs_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            os.environ["SIGNALLOCK_PROJECT_ROOT"] = str(self.repo_root)
            get_project_root.cache_clear()

            self.assertEqual(get_project_root(), self.repo_root)
            self.assertTrue(config_path("policy_profiles.json").exists())
            self.assertGreaterEqual(len(load_policy_configs()), 3)
            self.assertGreaterEqual(len(load_presets()), 1)

    def test_repo_root_is_detected_from_source_checkout(self) -> None:
        os.chdir(self.repo_root)
        os.environ.pop("SIGNALLOCK_PROJECT_ROOT", None)
        get_project_root.cache_clear()

        self.assertEqual(get_project_root(), self.repo_root)
        self.assertTrue(config_path("experiment_presets.json").exists())


if __name__ == "__main__":
    unittest.main()
