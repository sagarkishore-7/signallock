"""Tests for entity resolution and token extraction."""

from __future__ import annotations

import unittest

from signallock.core.enums import RoleSeniority, SourceClass, TokenBucket
from signallock.resolve import extract_token_buckets, resolve_subject

from ._fixtures import SUBJECT_ID, make_observations


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = resolve_subject(SUBJECT_ID, make_observations())

    def test_personal_trivia_collected(self) -> None:
        trivia = self.subject.tokens(TokenBucket.PERSONAL_TRIVIA)
        self.assertIn("rex", trivia)
        self.assertIn("redsox", trivia)  # collapsed multiword form
        self.assertIn("sox", trivia)

    def test_temporal_year_and_suffix(self) -> None:
        temporal = self.subject.tokens(TokenBucket.TEMPORAL)
        self.assertIn("2014", temporal)
        self.assertIn("14", temporal)  # 2-digit suffix

    def test_identity_tokens_from_username_and_email(self) -> None:
        identity = self.subject.tokens(TokenBucket.IDENTITY)
        self.assertIn("ghostrider", identity)

    def test_seniority_resolved_from_title(self) -> None:
        self.assertEqual(self.subject.role_seniority, RoleSeniority.DIRECTOR)

    def test_source_coverage_and_platforms(self) -> None:
        self.assertIn(SourceClass.SOCIAL, self.subject.source_coverage)
        self.assertGreaterEqual(self.subject.source_coverage[SourceClass.SOCIAL], 4)
        self.assertGreaterEqual(self.subject.platform_count, 3)

    def test_presence_only_excluded_from_tokens(self) -> None:
        # The github presence signal must not leak into any token bucket.
        self.assertNotIn("github", self.subject.all_tokens())

    def test_extract_buckets_directly(self) -> None:
        buckets = extract_token_buckets(make_observations())
        self.assertIn("rex", buckets[TokenBucket.PERSONAL_TRIVIA])


if __name__ == "__main__":
    unittest.main()
