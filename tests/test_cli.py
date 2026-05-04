"""CLI tests for SignalLock."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from signallock.cli import main


class CLITests(unittest.TestCase):
    """Smoke-test the Phase 1 CLI workflows."""

    def test_score_exposure_outputs_json(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(["score-exposure", "--count", "2", "--seed", "3", "--pretty"])

        decoded = json.loads(stream.getvalue())
        self.assertEqual(len(decoded), 2)
        self.assertIn("score", decoded[0])
        self.assertIn("band", decoded[0])

    def test_score_password_outputs_profile_and_assessment(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(
                [
                    "score-password",
                    "--password",
                    "Priya2024!",
                    "--count",
                    "2",
                    "--seed",
                    "3",
                    "--profile-index",
                    "0",
                    "--pretty",
                ]
            )

        decoded = json.loads(stream.getvalue())
        self.assertIn("profile", decoded)
        self.assertIn("assessment", decoded)
        self.assertIn("score", decoded["assessment"])

    def test_recommend_hardening_outputs_recommendation(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(
                [
                    "recommend-hardening",
                    "--password",
                    "Priya2014!",
                    "--count",
                    "3",
                    "--seed",
                    "1",
                    "--profile-index",
                    "0",
                    "--policy-profile",
                    "strict",
                    "--pretty",
                ]
            )

        decoded = json.loads(stream.getvalue())
        self.assertIn("exposure", decoded)
        self.assertIn("password_assessment", decoded)
        self.assertIn("policy_config", decoded)
        self.assertIn("recommendation", decoded)
        self.assertIn("primary_action", decoded["recommendation"])
        self.assertEqual(decoded["recommendation"]["policy_profile"], "strict")

    def test_list_policy_profiles_outputs_json(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(["list-policy-profiles", "--pretty"])

        decoded = json.loads(stream.getvalue())
        self.assertGreaterEqual(len(decoded), 3)
        self.assertIn("profile", decoded[0])

    def test_evaluate_policies_outputs_summaries(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(
                [
                    "evaluate-policies",
                    "--count",
                    "3",
                    "--seed",
                    "1",
                    "--policy-profiles",
                    "balanced",
                    "strict",
                    "--pretty",
                ]
            )

        decoded = json.loads(stream.getvalue())
        self.assertIn("summaries", decoded)
        self.assertEqual(len(decoded["summaries"]), 2)
        self.assertIn("policy_profile", decoded["summaries"][0])
        self.assertIn("average_combined_score", decoded["summaries"][0])

    def test_evaluate_policies_can_save_run(self) -> None:
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "evaluate-policies",
                        "--count",
                        "2",
                        "--seed",
                        "1",
                        "--save-run",
                        "--include-table",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(stream.getvalue())
            self.assertIn("artifacts", decoded)
            self.assertIn("comparison_table_markdown", decoded)
            self.assertTrue(Path(decoded["artifacts"]["report_file"]).exists())
            self.assertTrue(Path(decoded["artifacts"]["comparison_table_file"]).exists())

    def test_analyze_runs_outputs_overview_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluate_stream = io.StringIO()
            with contextlib.redirect_stdout(evaluate_stream):
                main(
                    [
                        "evaluate-policies",
                        "--count",
                        "2",
                        "--seed",
                        "1",
                        "--save-run",
                        "--output-dir",
                        temp_dir,
                    ]
                )

            analysis_stream = io.StringIO()
            with contextlib.redirect_stdout(analysis_stream):
                main(
                    [
                        "analyze-runs",
                        "--input-dir",
                        temp_dir,
                        "--include-rows",
                        "--include-table",
                        "--save-analysis",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(analysis_stream.getvalue())
            self.assertIn("overview", decoded)
            self.assertIn("rows", decoded)
            self.assertIn("comparison_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertEqual(decoded["overview"]["run_count"], 1)
            self.assertTrue(Path(decoded["artifacts"]["analysis_file"]).exists())

    def test_generate_figures_outputs_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluate_stream = io.StringIO()
            with contextlib.redirect_stdout(evaluate_stream):
                main(
                    [
                        "evaluate-policies",
                        "--count",
                        "2",
                        "--seed",
                        "1",
                        "--save-run",
                        "--output-dir",
                        temp_dir,
                    ]
                )

            figure_stream = io.StringIO()
            with contextlib.redirect_stdout(figure_stream):
                main(
                    [
                        "generate-figures",
                        "--input-dir",
                        temp_dir,
                        "--include-aggregates",
                        "--include-table",
                        "--save-figures",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(figure_stream.getvalue())
            self.assertIn("overview", decoded)
            self.assertIn("aggregates", decoded)
            self.assertIn("summary_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertTrue(Path(decoded["artifacts"]["score_chart_file"]).exists())

    def test_compare_policies_outputs_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluate_stream = io.StringIO()
            with contextlib.redirect_stdout(evaluate_stream):
                main(
                    [
                        "evaluate-policies",
                        "--count",
                        "2",
                        "--seed",
                        "1",
                        "--save-run",
                        "--output-dir",
                        temp_dir,
                    ]
                )

            comparison_stream = io.StringIO()
            with contextlib.redirect_stdout(comparison_stream):
                main(
                    [
                        "compare-policies",
                        "--input-dir",
                        temp_dir,
                        "--baseline-profile",
                        "balanced",
                        "--candidate-profiles",
                        "strict",
                        "--include-run-deltas",
                        "--include-table",
                        "--save-comparison",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(comparison_stream.getvalue())
            self.assertIn("overview", decoded)
            self.assertIn("summaries", decoded)
            self.assertIn("run_deltas", decoded)
            self.assertIn("comparison_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertTrue(Path(decoded["artifacts"]["delta_chart_file"]).exists())

    def test_list_experiment_presets_outputs_json(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(["list-experiment-presets", "--pretty"])

        decoded = json.loads(stream.getvalue())
        self.assertGreaterEqual(len(decoded), 3)
        self.assertIn("name", decoded[0])

    def test_run_preset_outputs_full_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = Path(temp_dir) / "presets.json"
            preset_file.write_text(
                json.dumps(
                    {
                        "presets": [
                            {
                                "name": "mini_suite",
                                "description": "Small preset for automated CLI coverage.",
                                "organization": "ExampleCorp",
                                "profile_count": 2,
                                "seeds": [1, 2],
                                "policy_profiles": ["balanced", "strict"],
                                "baseline_profile": "balanced",
                                "comparison_candidates": ["strict"],
                                "include_records": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "run-preset",
                        "--preset",
                        "mini_suite",
                        "--preset-file",
                        str(preset_file),
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(stream.getvalue())
            self.assertEqual(decoded["preset_name"], "mini_suite")
            self.assertEqual(decoded["evaluation_run_count"], 2)
            self.assertIn("analysis_artifacts", decoded)
            self.assertIn("figure_artifacts", decoded)
            self.assertIn("preset_artifacts", decoded)
            self.assertTrue(Path(decoded["preset_artifacts"]["manifest_file"]).exists())

    def test_summarize_presets_outputs_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = Path(temp_dir) / "presets.json"
            preset_file.write_text(
                json.dumps(
                    {
                        "presets": [
                            {
                                "name": "mini_suite",
                                "description": "Small preset for preset-summary CLI coverage.",
                                "organization": "ExampleCorp",
                                "profile_count": 2,
                                "seeds": [1, 2],
                                "policy_profiles": ["balanced", "strict"],
                                "baseline_profile": "balanced",
                                "comparison_candidates": ["strict"],
                                "include_records": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            run_stream = io.StringIO()
            with contextlib.redirect_stdout(run_stream):
                main(
                    [
                        "run-preset",
                        "--preset",
                        "mini_suite",
                        "--preset-file",
                        str(preset_file),
                        "--output-dir",
                        temp_dir,
                    ]
                )

            summary_stream = io.StringIO()
            with contextlib.redirect_stdout(summary_stream):
                main(
                    [
                        "summarize-presets",
                        "--input-dir",
                        temp_dir,
                        "--preset-names",
                        "mini_suite",
                        "--include-runs",
                        "--include-policy-summaries",
                        "--include-comparison-summaries",
                        "--include-tables",
                        "--save-summary",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(summary_stream.getvalue())
            self.assertIn("overview", decoded)
            self.assertIn("preset_runs", decoded)
            self.assertIn("policy_summaries", decoded)
            self.assertIn("comparison_summaries", decoded)
            self.assertIn("preset_table_markdown", decoded)
            self.assertIn("policy_table_markdown", decoded)
            self.assertIn("comparison_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertTrue(Path(decoded["artifacts"]["summary_file"]).exists())

    def test_aggregate_presets_outputs_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preset_file = Path(temp_dir) / "presets.json"
            preset_file.write_text(
                json.dumps(
                    {
                        "presets": [
                            {
                                "name": "mini_strict",
                                "description": "Small strict-focused preset for aggregate CLI coverage.",
                                "organization": "ExampleCorp",
                                "profile_count": 2,
                                "seeds": [1, 2],
                                "policy_profiles": ["balanced", "strict"],
                                "baseline_profile": "balanced",
                                "comparison_candidates": ["strict"],
                                "include_records": False,
                            },
                            {
                                "name": "mini_usability",
                                "description": "Small usability-focused preset for aggregate CLI coverage.",
                                "organization": "ExampleCorp",
                                "profile_count": 2,
                                "seeds": [1, 2],
                                "policy_profiles": ["balanced", "usability"],
                                "baseline_profile": "balanced",
                                "comparison_candidates": ["usability"],
                                "include_records": False,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            for preset_name in ("mini_strict", "mini_usability"):
                run_stream = io.StringIO()
                with contextlib.redirect_stdout(run_stream):
                    main(
                        [
                            "run-preset",
                            "--preset",
                            preset_name,
                            "--preset-file",
                            str(preset_file),
                            "--output-dir",
                            temp_dir,
                        ]
                    )

            aggregate_stream = io.StringIO()
            with contextlib.redirect_stdout(aggregate_stream):
                main(
                    [
                        "aggregate-presets",
                        "--input-dir",
                        temp_dir,
                        "--include-tables",
                        "--save-aggregates",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(aggregate_stream.getvalue())
            self.assertIn("overview", decoded)
            self.assertIn("preset_policy_aggregates", decoded)
            self.assertIn("preset_comparison_aggregates", decoded)
            self.assertIn("cross_policy_aggregates", decoded)
            self.assertIn("cross_comparison_aggregates", decoded)
            self.assertIn("preset_policy_table_markdown", decoded)
            self.assertIn("cross_policy_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertTrue(Path(decoded["artifacts"]["summary_file"]).exists())


if __name__ == "__main__":
    unittest.main()
