"""Web profile: the defensive mirror of personal-site / blog harvesting.

An attacker reads a target's own personal site or blog for interests, projects,
and biographical detail that seed a guess list. The defensive mirror fetches
only an *owned* URL derived from ``identity.seeds.domain`` through an injectable
client, extracts visible text with ``bs4`` (guarded as an optional dependency),
and emits INTEREST tokens. Offline-first default with no client: ``[]``.
"""

from __future__ import annotations

import re

from ..core.enums import AttributeKind, SourceClass
from ..core.errors import CollectorError, require_dependency
from ..core.evidence import Observation
from ..core.identity import ConsentedIdentity
from .base import Collector, register

#: Drop short/common tokens that carry no guessing value.
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "this", "that", "from", "your", "you",
        "are", "was", "were", "have", "has", "but", "not", "all", "any",
        "our", "out", "about", "more", "into", "their", "here", "what",
    }
)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]{2,}")


@register
class WebProfile(Collector):
    """Fetch an owned personal site and emit INTEREST tokens from its text.

    The fetched URL is built from ``identity.seeds.domain`` (an owned domain).
    Text extraction uses ``bs4``, guarded via :func:`require_dependency`. With no
    injected client the collector stays offline and returns ``[]``.
    """

    source = SourceClass.WEB
    mirrors = "personal-site"

    def __init__(self, *, client=None, max_tokens: int = 25) -> None:
        self._client = client
        self._max_tokens = max_tokens

    def _collect(self, identity: ConsentedIdentity) -> list[Observation]:
        domain = identity.seeds.domain
        if not domain or self._client is None:
            # Offline-first: no owned domain or no injected client → nothing.
            return []

        url = domain if domain.startswith("http") else f"https://{domain}"
        try:
            response = self._client.get(url)
            response.raise_for_status()
            html = response.text
        except CollectorError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise transport errors
            raise CollectorError(f"Web fetch failed for {url}: {exc}") from exc

        require_dependency("bs4", "osint")
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        observations: list[Observation] = []
        seen: set[str] = set()
        for match in _TOKEN_RE.finditer(text):
            token = match.group(0)
            key = token.lower()
            if key in _STOPWORDS or key in seen:
                continue
            seen.add(key)
            observations.append(
                self._obs(
                    identity.subject_id,
                    AttributeKind.INTEREST,
                    token,
                    confidence=0.4,
                    provenance=f"web:{url}",
                )
            )
            if len(observations) >= self._max_tokens:
                break
        return observations
