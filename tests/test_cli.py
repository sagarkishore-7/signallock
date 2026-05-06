"""CLI tests for SignalLock."""

from __future__ import annotations

import csv
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from signallock.cli import main
from signallock.dataset import dataset_to_csv, generate_dataset
from signallock.expert_review import generate_review_tasks, write_review_tasks_csv
from signallock.model import save_model, train_model
from signallock.synthetic_profiles import generate_synthetic_profiles


class CLITests(unittest.TestCase):
    """Smoke-test the Phase 1 CLI workflows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.review_profiles = generate_synthetic_profiles(count=2, seed=1)
        _, cls.review_records = generate_dataset(cls.review_profiles, seed=1)
        training_result, fitted_model = train_model(
            cls.review_records,
            model_type="gradient_boosting",
            random_state=1,
        )
        cls._model_temp_dir = tempfile.TemporaryDirectory()
        artifacts = save_model(
            fitted_model,
            training_result,
            output_dir=cls._model_temp_dir.name,
        )
        cls.review_model_file = artifacts.model_file

    @classmethod
    def tearDownClass(cls) -> None:
        cls._model_temp_dir.cleanup()

    def _write_dataset_records_csv(self, temp_dir: str) -> Path:
        path = Path(temp_dir) / "dataset_records.csv"
        path.write_text(dataset_to_csv(self.review_records), encoding="utf-8")
        return path

    def _write_completed_review_csv(
        self,
        temp_dir: str,
        *,
        include_ml: bool,
        band_source: str = "ml",
        filename: str = "completed_review.csv",
    ) -> Path:
        tasks = generate_review_tasks(
            self.review_profiles,
            model_file=self.review_model_file if include_ml else None,
        )
        rows = list(csv.DictReader(io.StringIO(write_review_tasks_csv(tasks))))
        for row in rows:
            if band_source == "ml":
                row["expert_band"] = row["ml_predicted_band"] or row["heuristic_band"]
            elif band_source == "heuristic":
                row["expert_band"] = row["heuristic_band"]
            else:
                raise ValueError(f"unknown band_source: {band_source}")

        path = Path(temp_dir) / filename
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_score_exposure_outputs_json(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main(["score-exposure", "--count", "2", "--seed", "3", "--pretty"])

        decoded = json.loads(stream.getvalue())
        self.assertEqual(len(decoded), 2)
        self.assertIn("score", decoded[0])
        self.assertIn("band", decoded[0])

    def test_main_without_command_prints_current_guidance(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            main([])

        output = stream.getvalue()
        self.assertIn("defensive research prototype", output)
        self.assertIn("evaluate-policies --count 5 --seed 1 --pretty", output)
        self.assertIn(".venv/bin/python", output)

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

    def test_generate_review_tasks_with_model_file_embeds_ml_band_column(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "tasks.csv"
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "generate-review-tasks",
                        "--count",
                        "2",
                        "--seed",
                        "1",
                        "--model-file",
                        str(self.review_model_file),
                        "--format",
                        "csv",
                        "--output-file",
                        str(output_file),
                    ]
                )

            decoded = json.loads(stream.getvalue())
            with output_file.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(decoded["tasks_written"], 20)
            self.assertTrue(any(row["ml_predicted_band"] for row in rows))

    def test_generate_review_tasks_blind_review_writes_hidden_packet_and_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "tasks_blind.csv"
            key_file = Path(temp_dir) / "tasks_key.json"
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "generate-review-tasks",
                        "--count",
                        "2",
                        "--seed",
                        "1",
                        "--model-file",
                        str(self.review_model_file),
                        "--blind-review",
                        "--key-output-file",
                        str(key_file),
                        "--format",
                        "csv",
                        "--output-file",
                        str(output_file),
                    ]
                )

            decoded = json.loads(stream.getvalue())
            with output_file.open(encoding="utf-8") as fh:
                blind_rows = list(csv.DictReader(fh))
            key_payload = json.loads(key_file.read_text(encoding="utf-8"))
            self.assertTrue(decoded["blind_review"])
            self.assertEqual(decoded["key_output_file"], str(key_file))
            self.assertEqual(blind_rows[0]["heuristic_band"], "")
            self.assertEqual(blind_rows[0]["heuristic_action"], "")
            self.assertEqual(blind_rows[0]["ml_predicted_band"], "")
            self.assertNotEqual(key_payload["tasks"][0]["heuristic_band"], "")

    def test_generate_review_tasks_blind_review_requires_key_output_file(self) -> None:
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            with contextlib.redirect_stderr(devnull):
                with self.assertRaises(SystemExit) as exc:
                    main(
                        [
                            "generate-review-tasks",
                            "--count",
                            "2",
                            "--seed",
                            "1",
                            "--blind-review",
                            "--format",
                            "csv",
                        ]
                    )
        self.assertEqual(exc.exception.code, 2)

    def test_compute_external_calibration_requires_embedded_ml_when_model_file_is_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records_file = self._write_dataset_records_csv(temp_dir)
            ratings_file = self._write_completed_review_csv(temp_dir, include_ml=False)

            with open(os.devnull, "w", encoding="utf-8") as devnull:
                with contextlib.redirect_stderr(devnull):
                    with self.assertRaises(SystemExit) as exc:
                        main(
                            [
                                "compute-external-calibration",
                                "--records-file",
                                str(records_file),
                                "--ratings-file",
                                str(ratings_file),
                                "--model-file",
                                str(self.review_model_file),
                            ]
                        )

            self.assertEqual(exc.exception.code, 2)

    def test_compute_external_calibration_uses_embedded_ml_bands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records_file = self._write_dataset_records_csv(temp_dir)
            ratings_file = self._write_completed_review_csv(temp_dir, include_ml=True)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "compute-external-calibration",
                        "--records-file",
                        str(records_file),
                        "--ratings-file",
                        str(ratings_file),
                        "--model-file",
                        str(self.review_model_file),
                        "--pretty",
                    ]
                )

            decoded = json.loads(stream.getvalue())
            self.assertEqual(decoded["rating_count"], 20)
            self.assertEqual(decoded["ml_vs_expert_match_rate"], 1.0)
            self.assertIn("ml_band_distribution", decoded)

    def test_compute_external_calibration_blind_review_can_use_reference_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records_file = self._write_dataset_records_csv(temp_dir)
            blind_packet = Path(temp_dir) / "blind_tasks.csv"
            key_file = Path(temp_dir) / "blind_tasks_key.json"

            with contextlib.redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-review-tasks",
                        "--count",
                        "2",
                        "--seed",
                        "1",
                        "--model-file",
                        str(self.review_model_file),
                        "--blind-review",
                        "--key-output-file",
                        str(key_file),
                        "--format",
                        "csv",
                        "--output-file",
                        str(blind_packet),
                    ]
                )

            with blind_packet.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            for row in rows:
                row["expert_band"] = "LOW"
            completed_file = Path(temp_dir) / "blind_completed.csv"
            with completed_file.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "compute-external-calibration",
                        "--records-file",
                        str(records_file),
                        "--ratings-file",
                        str(completed_file),
                        "--model-file",
                        str(self.review_model_file),
                        "--reference-file",
                        str(key_file),
                        "--pretty",
                    ]
                )

            decoded = json.loads(stream.getvalue())
            self.assertEqual(decoded["rating_count"], 20)
            self.assertIn("ml_band_distribution", decoded)

    def test_summarize_expert_reviews_outputs_summary_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records_file = self._write_dataset_records_csv(temp_dir)
            reviewer_a = self._write_completed_review_csv(
                temp_dir,
                include_ml=True,
                band_source="heuristic",
                filename="reviewer_a.csv",
            )
            reviewer_b = self._write_completed_review_csv(
                temp_dir,
                include_ml=True,
                band_source="ml",
                filename="reviewer_b.csv",
            )
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "summarize-expert-reviews",
                        "--records-file",
                        str(records_file),
                        "--ratings-files",
                        str(reviewer_a),
                        str(reviewer_b),
                        "--model-file",
                        str(self.review_model_file),
                        "--include-reviewer-summaries",
                        "--include-consensus-tasks",
                        "--include-table",
                        "--save-summary",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(stream.getvalue())
            self.assertEqual(decoded["overview"]["reviewer_count"], 2)
            self.assertIn("reviewer_summaries", decoded)
            self.assertIn("consensus_tasks", decoded)
            self.assertIn("summary_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertTrue(Path(decoded["artifacts"]["summary_file"]).exists())

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
        self.assertIn("calibration_summaries", decoded)
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
            self.assertIn("calibration_table_markdown", decoded)
            self.assertIn("calibration_summaries", decoded)
            self.assertTrue(Path(decoded["artifacts"]["report_file"]).exists())
            self.assertTrue(Path(decoded["artifacts"]["comparison_table_file"]).exists())
            self.assertTrue(Path(decoded["artifacts"]["calibration_summaries_file"]).exists())
            self.assertTrue(Path(decoded["artifacts"]["calibration_table_file"]).exists())

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
            self.assertIn("calibration_rows", decoded)
            self.assertIn("comparison_table_markdown", decoded)
            self.assertIn("calibration_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertEqual(decoded["overview"]["run_count"], 1)
            self.assertTrue(Path(decoded["artifacts"]["analysis_file"]).exists())
            self.assertTrue(Path(decoded["artifacts"]["calibration_table_file"]).exists())
            self.assertTrue(Path(decoded["artifacts"]["calibration_matrix_file"]).exists())

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
            self.assertIn("calibration_summaries", decoded)
            self.assertIn("comparison_summaries", decoded)
            self.assertIn("preset_table_markdown", decoded)
            self.assertIn("policy_table_markdown", decoded)
            self.assertIn("calibration_table_markdown", decoded)
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
            self.assertIn("preset_calibration_aggregates", decoded)
            self.assertIn("preset_comparison_aggregates", decoded)
            self.assertIn("cross_policy_aggregates", decoded)
            self.assertIn("cross_calibration_aggregates", decoded)
            self.assertIn("cross_comparison_aggregates", decoded)
            self.assertIn("preset_policy_table_markdown", decoded)
            self.assertIn("preset_calibration_table_markdown", decoded)
            self.assertIn("cross_policy_table_markdown", decoded)
            self.assertIn("cross_calibration_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertTrue(Path(decoded["artifacts"]["summary_file"]).exists())

    def test_sweep_thresholds_outputs_artifacts(self) -> None:
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            with contextlib.redirect_stdout(stream):
                main(
                    [
                        "sweep-thresholds",
                        "--base-profile",
                        "balanced",
                        "--count",
                        "3",
                        "--seed",
                        "1",
                        "--threshold-offsets",
                        "-8",
                        "0",
                        "8",
                        "--include-table",
                        "--save-sweep",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(stream.getvalue())
            self.assertIn("overview", decoded)
            self.assertIn("records", decoded)
            self.assertIn("table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertEqual(decoded["overview"]["variant_count"], 3)
            self.assertTrue(Path(decoded["artifacts"]["summary_file"]).exists())

    def test_analyze_threshold_sweeps_outputs_artifacts(self) -> None:
        sweep_stream = io.StringIO()
        analysis_stream = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            with contextlib.redirect_stdout(sweep_stream):
                main(
                    [
                        "sweep-thresholds",
                        "--base-profile",
                        "balanced",
                        "--count",
                        "3",
                        "--seed",
                        "1",
                        "--threshold-offsets",
                        "-8",
                        "0",
                        "8",
                        "--save-sweep",
                        "--output-dir",
                        temp_dir,
                    ]
                )

            with contextlib.redirect_stdout(analysis_stream):
                main(
                    [
                        "analyze-threshold-sweeps",
                        "--input-dir",
                        temp_dir,
                        "--include-rows",
                        "--include-aggregates",
                        "--include-tables",
                        "--save-analysis",
                        "--output-dir",
                        temp_dir,
                        "--pretty",
                    ]
                )

            decoded = json.loads(analysis_stream.getvalue())
            self.assertIn("overview", decoded)
            self.assertIn("rows", decoded)
            self.assertIn("aggregates", decoded)
            self.assertIn("run_table_markdown", decoded)
            self.assertIn("aggregate_table_markdown", decoded)
            self.assertIn("artifacts", decoded)
            self.assertEqual(decoded["overview"]["run_count"], 1)
            self.assertTrue(Path(decoded["artifacts"]["summary_file"]).exists())

    def test_generate_threshold_sweep_figures_outputs_artifacts(self) -> None:
        sweep_stream = io.StringIO()
        figure_stream = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            with contextlib.redirect_stdout(sweep_stream):
                main(
                    [
                        "sweep-thresholds",
                        "--base-profile",
                        "balanced",
                        "--count",
                        "3",
                        "--seed",
                        "1",
                        "--threshold-offsets",
                        "-8",
                        "0",
                        "8",
                        "--save-sweep",
                        "--output-dir",
                        temp_dir,
                    ]
                )

            with contextlib.redirect_stdout(figure_stream):
                main(
                    [
                        "generate-threshold-sweep-figures",
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
            self.assertEqual(decoded["overview"]["run_count"], 1)
            self.assertTrue(Path(decoded["artifacts"]["summary_file"]).exists())


if __name__ == "__main__":
    unittest.main()
