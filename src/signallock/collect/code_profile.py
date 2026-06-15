"""Code-host collector: the defensive mirror of GitHub OSINT.

Reproduces what an attacker harvests from a target's public code host (the
``github-api`` / ``gitrecon`` step): real name, employer, location, the
languages they write and the project names/topics they care about — all prime
seeds for a personalised guess list. Uses the public GitHub REST API through an
*injectable* ``httpx``-style client so tests run fully offline.
"""

from __future__ import annotations

import os

from ..core.enums import AttributeKind, SourceClass
from ..core.errors import CollectorError, require_dependency
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register

_API_ROOT = "https://api.github.com"

#: Only the most prominent repos seed interest tokens. Auto-scraped repo
#: names/topics are noisy guessing material, and a targeted attacker focuses on a
#: subject's most visible projects rather than every fork or throwaway repo.
_INTEREST_REPO_CAP = 12


@register
class CodeProfile(Collector):
    """Harvest public profile + repo signals from GitHub.

    The live path is gated only by consent (public, ToS-permitted API). Tests
    inject a fake client; production uses a default :class:`httpx.Client`.
    """

    source = SourceClass.CODE
    mirrors = "github-api"

    def __init__(self, *, client=None, token: str | None = None) -> None:
        self._client = client
        self._token = token if token is not None else os.environ.get("GITHUB_TOKEN")

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        require_dependency("httpx", "osint")
        import httpx

        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.Client(headers=headers, timeout=10.0)
        return self._client

    def _get_json(self, url: str):
        client = self._ensure_client()
        try:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
        except CollectorError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise any client/transport error
            raise CollectorError(f"GitHub request failed for {url}: {exc}") from exc

    def _collect(self, identity: ConsentedIdentity) -> list[Observation]:
        username = identity.seeds.username
        if not username:
            return []

        observations: list[Observation] = []
        sid = identity.subject_id

        profile = self._get_json(f"{_API_ROOT}/users/{username}")
        if not isinstance(profile, dict):
            raise CollectorError("Unexpected GitHub user payload (not an object)")

        observations.append(
            self._obs(
                sid,
                AttributeKind.USERNAME,
                username,
                confidence=0.99,
                provenance=f"github:{username}",
            )
        )
        for field, kind, conf in (
            ("name", AttributeKind.NAME, 0.85),
            ("company", AttributeKind.ORGANIZATION, 0.8),
            ("location", AttributeKind.LOCATION, 0.8),
        ):
            value = profile.get(field)
            if value and str(value).strip():
                observations.append(
                    self._obs(
                        sid,
                        kind,
                        str(value).lstrip("@").strip(),
                        confidence=conf,
                        provenance=f"github:{username}",
                    )
                )

        repos = self._get_json(f"{_API_ROOT}/users/{username}/repos")
        repos = [r for r in repos if isinstance(r, dict)] if isinstance(repos, list) else []
        # Rank by prominence (stars, then most-recently pushed) so the subject's
        # most visible projects seed interests first; only the top repos do, and
        # forks are skipped as weak personal signal.
        repos.sort(
            key=lambda r: (
                int(r.get("stargazers_count") or 0),
                str(r.get("pushed_at") or ""),
            ),
            reverse=True,
        )

        seen_languages: set[str] = set()
        for rank, repo in enumerate(repos):
            language = repo.get("language")
            if language and str(language).strip():
                key = str(language).strip().lower()
                if key not in seen_languages:
                    seen_languages.add(key)
                    observations.append(
                        self._obs(
                            sid,
                            AttributeKind.LANGUAGE,
                            str(language).strip(),
                            confidence=0.7,
                            provenance=f"github:{username}/repos",
                        )
                    )
            # Languages are read from every repo; interests only from the top,
            # non-fork repos.
            if rank >= _INTEREST_REPO_CAP or repo.get("fork"):
                continue
            name = repo.get("name")
            if name and str(name).strip():
                observations.append(
                    self._obs(
                        sid,
                        AttributeKind.INTEREST,
                        str(name).strip(),
                        confidence=0.5,
                        provenance=f"github:{username}/{name}",
                    )
                )
            for topic in repo.get("topics", []) or []:
                if topic and str(topic).strip():
                    observations.append(
                        self._obs(
                            sid,
                            AttributeKind.INTEREST,
                            str(topic).strip(),
                            confidence=0.5,
                            provenance=f"github:{username}/{name}#topics",
                        )
                    )
        return observations
