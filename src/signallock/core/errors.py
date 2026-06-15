"""Exception hierarchy for SignalLock v2."""

from __future__ import annotations


class SignalLockError(Exception):
    """Base class for all SignalLock errors."""


class ConsentError(SignalLockError):
    """Raised when an operation targets an identity outside the consent roster.

    The consent gate (`core.identity.require_consent`) raises this before any
    collector reads a network source or the guess simulator runs against a
    password. It is the hard ethical boundary of the whole system.
    """


class CollectorError(SignalLockError):
    """Raised when a collector fails irrecoverably (network, parse, auth)."""


class DependencyError(SignalLockError):
    """Raised when an optional dependency is required but not installed."""


def require_dependency(module_name: str, extra: str) -> None:
    """Raise a helpful :class:`DependencyError` if ``module_name`` is missing.

    Mirrors the v1 ``_require_sklearn`` pattern: optional features degrade with a
    clear install hint rather than an opaque ``ImportError``.
    """
    import importlib.util

    if importlib.util.find_spec(module_name) is None:
        raise DependencyError(
            f"'{module_name}' is required for this feature. "
            f'Install it with: pip install "signallock[{extra}]"'
        )
