"""Tests for the evaluation harness: dataset, metrics, ablation, expert packet."""

from __future__ import annotations

import unittest

from signallock.core.identity import ConsentRoster
from signallock.eval import (
    ablation_study,
    build_dataset,
    build_expert_packet,
    evaluate_dataset,
)

from ._fixtures import SUBJECT_ID, make_identity, make_observations


def _roster_and_data():
    """Two consented subjects with enough passwords to train a model."""
    identity = make_identity()
    roster = ConsentRoster({identity.subject_id: identity.consent})
    # Reuse the same observation set for a second subject id to get >= 8 rows.
    obs_a = make_observations(SUBJECT_ID)
    second = "dummy-twin"
    obs_b = make_observations(second)
    roster.add(make_identity(second).consent)
    observations = {SUBJECT_ID: obs_a, second: obs_b}
    passwords = {
        SUBJECT_ID: ["rex2014", "redsox2014", "fox2014", "9f!Qz#7vLp2@Xw"],
        second: ["rex2014", "redsox2014", "fox2014", "Zp3!xK9#wL2vRm"],
    }
    return roster, observations, passwords


class DatasetTests(unittest.TestCase):
    def test_build_dataset_labels_and_no_passwords(self) -> None:
        roster, observations, passwords = _roster_and_data()
        dataset = build_dataset(observations, passwords, roster)
        self.assertEqual(len(dataset), 8)
        # Labels include both cracked and survived passwords.
        self.assertIn("LOW", dataset.labels())
        self.assertTrue(any(b != "LOW" for b in dataset.labels()))
        # No password strings leak into the exported records.
        blob = str(dataset.to_records())
        self.assertNotIn("rex2014", blob)
        self.assertNotIn("redsox2014", blob)

    def test_non_roster_subject_excluded(self) -> None:
        roster, observations, passwords = _roster_and_data()
        observations["intruder"] = make_observations("intruder")
        passwords["intruder"] = ["whatever"]
        dataset = build_dataset(observations, passwords, roster)
        self.assertNotIn("intruder", {r.subject_id for r in dataset.rows})


class MetricsTests(unittest.TestCase):
    def test_evaluate_dataset_reports_premium_and_model(self) -> None:
        roster, observations, passwords = _roster_and_data()
        dataset = build_dataset(observations, passwords, roster)
        report = evaluate_dataset(dataset)
        self.assertEqual(report["sample_count"], 8)
        self.assertIn("premium", report)
        self.assertIn("model", report)  # may carry an error for tiny data; key exists

    def test_ablation_axes_present_and_nonnegative(self) -> None:
        roster, observations, _ = _roster_and_data()
        result = ablation_study(observations, roster)
        axes = result["axes"]
        self.assertIn("personal_trivia_richness", axes)
        self.assertIn("linkability", axes)
        for axis in axes.values():
            self.assertGreaterEqual(axis["mean_score_delta"], 0.0)


class ExpertTests(unittest.TestCase):
    def test_expert_packet_includes_password_and_heuristic_band(self) -> None:
        roster, observations, passwords = _roster_and_data()
        tasks = build_expert_packet(observations, passwords, roster)
        self.assertTrue(tasks)
        row = tasks[0].to_csv_row()
        self.assertIn("password", row)
        self.assertIn("heuristic_band", row)
        self.assertEqual(row["expert_band"], "")  # reviewer fills this


if __name__ == "__main__":
    unittest.main()
