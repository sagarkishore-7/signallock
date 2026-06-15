"""Entity resolution: observations -> a normalized Subject dossier."""

from __future__ import annotations

from .entity import resolve_subject
from .tokens import extract_token_buckets

__all__ = ["resolve_subject", "extract_token_buckets"]
