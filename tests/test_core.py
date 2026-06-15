"""Tests for the SignalLock v2 core: enums, consent gate, evidence, subjects."""

from __future__ import annotations

import unittest

from signallock.core import (
    AttributeKind,
    Budget,
    ConsentedIdentity,
    ConsentError,
    ConsentRecord,
    ConsentRoster,
    IdentitySeeds,
    Observation,
    RiskBand,
    SourceClass,
    Subject,
    TokenBucket,
    require_consent,
)
from signallock.core.enums import BUDGET_TO_BAND, RoleSeniority


def _identity(subject_id: str = "subj-1") -> ConsentedIdentity:
    return ConsentedIdentity(
        subject_id=subject_id,
        seeds=IdentitySeeds(username="ghost", email="ghost@example.com"),
        consent=ConsentRecord(
            subject_id=subject_id,
            consent_ref="consent/subj-1.pdf",
            granted_at="2026-06-01",
        ),
    )


class EnumTests(unittest.TestCase):
    def test_risk_band_ordering(self) -> None:
        self.assertLess(RiskBand.LOW, RiskBand.CRITICAL)
        self.assertEqual(max(RiskBand.LOW, RiskBand.HIGH), RiskBand.HIGH)
        self.assertEqual(RiskBand.MEDIUM.rank, 1)

    def test_seniority_rank(self) -> None:
        self.assertEqual(RoleSeniority.C_SUITE.rank, 4)
        self.assertGreater(
            RoleSeniority.VP.rank, RoleSeniority.INDIVIDUAL_CONTRIBUTOR.rank
        )

    def test_budget_ordered_and_band_mapping(self) -> None:
        self.assertEqual(Budget.ordered()[0], Budget.B1)
        self.assertEqual(Budget.ordered()[-1], Budget.B10000)
        self.assertEqual(BUDGET_TO_BAND[Budget.B1], RiskBand.CRITICAL)
        self.assertEqual(BUDGET_TO_BAND[None], RiskBand.LOW)


class ConsentTests(unittest.TestCase):
    def test_require_consent_passes_for_roster_member(self) -> None:
        identity = _identity()
        roster = ConsentRoster({identity.subject_id: identity.consent})
        self.assertIs(require_consent(identity, roster), identity.consent)

    def test_require_consent_refuses_non_member(self) -> None:
        roster = ConsentRoster()
        with self.assertRaises(ConsentError):
            require_consent(_identity(), roster)

    def test_source_allowlist_enforced(self) -> None:
        identity = ConsentedIdentity(
            subject_id="s2",
            seeds=IdentitySeeds(username="x"),
            consent=ConsentRecord(
                subject_id="s2",
                consent_ref="c",
                granted_at="2026-06-01",
                allowed_sources=frozenset({"CODE"}),
            ),
        )
        roster = ConsentRoster({"s2": identity.consent})
        require_consent(identity, roster, source="CODE")  # allowed
        with self.assertRaises(ConsentError):
            require_consent(identity, roster, source="SOCIAL")

    def test_roster_load_from_dicts(self) -> None:
        roster = ConsentRoster.from_dicts(
            [{"subject_id": "a", "consent_ref": "c", "granted_at": "2026-01-01"}]
        )
        self.assertIn("a", roster)
        self.assertEqual(roster.subject_ids(), ["a"])

    def test_identity_requires_matching_consent(self) -> None:
        with self.assertRaises(ValueError):
            ConsentedIdentity(
                subject_id="a",
                seeds=IdentitySeeds(username="x"),
                consent=ConsentRecord("b", "c", "2026-01-01"),
            )

    def test_seeds_require_at_least_one(self) -> None:
        with self.assertRaises(ValueError):
            IdentitySeeds()


class ObservationTests(unittest.TestCase):
    def test_validation_and_normalization(self) -> None:
        obs = Observation(
            subject_id="s1",
            source=SourceClass.SOCIAL,
            attr_kind=AttributeKind.PET_NAME,
            value="  Rex  ",
            confidence=0.8,
            collected_at="2026-06-01T00:00:00Z",
            provenance="snapshot:ig-1",
            mirrors="cupp",
        )
        self.assertEqual(obs.value, "Rex")  # trimmed, case preserved
        self.assertFalse(obs.is_presence_only)

    def test_confidence_bounds(self) -> None:
        with self.assertRaises(ValueError):
            Observation(
                "s1", SourceClass.CODE, AttributeKind.USERNAME, "x",
                1.5, "t", "p", "maigret",
            )

    def test_presence_only_flag(self) -> None:
        obs = Observation(
            "s1", SourceClass.USERNAME_ENUM, AttributeKind.PLATFORM_PRESENCE,
            "github", 1.0, "t", "p", "maigret",
        )
        self.assertTrue(obs.is_presence_only)


class SubjectTests(unittest.TestCase):
    def test_buckets_normalized_and_deduped(self) -> None:
        subject = Subject(
            subject_id="s1",
            token_buckets={
                TokenBucket.NAME: ["Alice", "alice", "  Bob "],
                TokenBucket.PERSONAL_TRIVIA: ["Rex"],
            },
        )
        self.assertEqual(subject.tokens(TokenBucket.NAME), ["alice", "bob"])
        self.assertEqual(subject.personal_trivia, ["rex"])
        # Every bucket is materialized even when empty.
        self.assertEqual(subject.tokens(TokenBucket.STRUCTURE_PRIOR), [])

    def test_all_tokens_dedupes_across_buckets(self) -> None:
        subject = Subject(
            subject_id="s1",
            token_buckets={
                TokenBucket.NAME: ["alice"],
                TokenBucket.IDENTITY: ["alice", "ghost"],
            },
        )
        self.assertEqual(sorted(subject.all_tokens()), ["alice", "ghost"])

    def test_to_dict_serializable(self) -> None:
        subject = Subject(subject_id="s1", platforms=[SourceClass.CODE])
        data = subject.to_dict()
        self.assertEqual(data["platforms"], ["CODE"])
        self.assertIn("name", data["token_buckets"])


if __name__ == "__main__":
    unittest.main()
