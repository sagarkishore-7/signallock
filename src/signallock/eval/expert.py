"""Expert-review packet: (subject summary, password) pairs for a human study.

Security professionals read a subject summary and a candidate password and judge
the targeted risk band. Their ratings provide an external calibration anchor for
the simulator's labels and the learned model — the three-way agreement study.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import TokenBucket
from ..core.evidence import Observation
from ..core.identity import (
    ConsentedIdentity,
    ConsentRoster,
    IdentitySeeds,
)
from ..core.subject import Subject
from ..exposure.model import assess_exposure
from ..predict.simulator import simulate_predictability
from ..resolve.entity import resolve_subject


def subject_summary(subject: Subject) -> str:
    """A short, reviewer-facing description of a subject's exposed footprint."""
    parts = [
        f"seniority={subject.role_seniority.value.lower()}",
        f"platforms={subject.platform_count}",
        f"trivia={len(subject.tokens(TokenBucket.PERSONAL_TRIVIA))}",
        f"temporal={len(subject.tokens(TokenBucket.TEMPORAL))}",
        f"breaches={subject.breach_count}",
    ]
    sample = subject.tokens(TokenBucket.PERSONAL_TRIVIA)[:3]
    if sample:
        parts.append("exposed_trivia=" + ",".join(sample))
    return "; ".join(parts)


@dataclass
class ReviewTask:
    """One task for an expert reviewer to rate."""

    task_id: str
    subject_id: str
    profile_summary: str
    password: str
    heuristic_band: str   # simulator band, for reference (do not bias the rater)

    def to_csv_row(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "subject_id": self.subject_id,
            "profile_summary": self.profile_summary,
            "password": self.password,
            "heuristic_band": self.heuristic_band,
            "expert_band": "",
            "notes": "",
        }


def build_expert_packet(
    observations_by_subject: dict[str, list[Observation]],
    passwords_by_subject: dict[str, list[str]],
    roster: ConsentRoster,
) -> list[ReviewTask]:
    """Build review tasks for every consented (subject, password) pair."""
    tasks: list[ReviewTask] = []
    counter = 0
    for subject_id, observations in observations_by_subject.items():
        if subject_id not in roster:
            continue
        subject = resolve_subject(subject_id, observations)
        assess_exposure(subject)  # ensures the subject resolves cleanly
        identity = ConsentedIdentity(
            subject_id=subject_id,
            seeds=IdentitySeeds(username=subject_id),
            consent=roster.get(subject_id),  # type: ignore[arg-type]
        )
        summary = subject_summary(subject)
        for password in passwords_by_subject.get(subject_id, []):
            prediction = simulate_predictability(
                subject, password, identity=identity, roster=roster
            )
            counter += 1
            tasks.append(
                ReviewTask(
                    task_id=f"task-{counter:04d}",
                    subject_id=subject_id,
                    profile_summary=summary,
                    password=password,
                    heuristic_band=prediction.band.value,
                )
            )
    return tasks
