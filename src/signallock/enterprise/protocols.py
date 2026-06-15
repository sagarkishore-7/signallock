"""Enterprise control-plane interfaces — DESIGN + STUBS ONLY for this phase.

SignalLock's research core (``collect`` -> ``resolve`` -> ``exposure`` /
``predict`` -> ``policy``) scores individual consented subjects. To run that core
as a multi-tenant enterprise service you need a control plane around it: tenant
isolation, identity-provider sync into a consented roster, policy-as-code
enforcement, an audit trail, SIEM export, and role/scope-based access control.

This module captures that trajectory as :class:`typing.Protocol` interfaces plus
*no-op reference implementations*. The Noop classes import cleanly and document
intent, but their real methods raise :class:`NotImplementedError`: there is no
tenant database, IdP integration, SIEM, or admin UI in this phase. See
``docs/ENTERPRISE_ARCHITECTURE.md`` for how each Protocol maps onto the research
core it wraps.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Protocol, runtime_checkable

from ..core import HardeningAction, RiskBand  # noqa: F401  (re-exported for design use)
from ..policy import HardeningRecommendation
from ..core import ConsentedIdentity, ConsentRoster  # noqa: F401  (re-exported)

__all__ = [
    "TenantContext",
    "tenant_scoped",
    "IdentitySync",
    "NoopIdentitySync",
    "PolicyEnforcer",
    "NoopPolicyEnforcer",
    "AuditSink",
    "NoopAuditSink",
    "SiemExporter",
    "NoopSiemExporter",
    "Role",
    "ApiKeyScope",
]


# --------------------------------------------------------------------------- #
# Multi-tenant isolation (design-only)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TenantContext:
    """Identifies the tenant a request/assessment is scoped to.

    In a real deployment every roster, observation, assessment, and audit event
    would be partitioned by ``tenant_id`` so one customer can never read or score
    another's subjects. This phase ships the identifier shape only.
    """

    tenant_id: str
    display_name: str


@contextmanager
def tenant_scoped(tenant_id: str) -> Iterator[TenantContext]:
    """Enter a tenant-isolated scope — STUB.

    A real implementation would bind the tenant's data partition (row-level
    security / per-tenant schema), credentials, and rate limits for the duration
    of the block. Multi-tenant isolation is design-only in this phase, so this
    raises immediately.
    """
    raise NotImplementedError(
        "multi-tenant isolation is design-only in this phase"
    )
    yield  # pragma: no cover - unreachable, present so this reads as a CM


# --------------------------------------------------------------------------- #
# IdP / directory sync -> consented roster
# --------------------------------------------------------------------------- #
@runtime_checkable
class IdentitySync(Protocol):
    """Maps an organization's directory into a consented roster.

    An enterprise customer's source of truth for "who works here" is their IdP
    (SSO via OIDC/SAML) and provisioning feed (SCIM). An implementation pulls
    users/groups from that directory and emits :class:`ConsentedIdentity`
    records — but only for subjects whose org policy / employment agreement
    grants assessment consent, preserving the consent gate the research core
    enforces.
    """

    def sync(self) -> list[ConsentedIdentity]:
        """Return the consented identities resolved from the org directory."""
        ...


class NoopIdentitySync:
    """No-op :class:`IdentitySync` — STUB.

    Rostering from an IdP works by reading SCIM-provisioned users (and SSO/OIDC
    group claims), reconciling them against the org's documented assessment
    consent, and producing one :class:`ConsentedIdentity` per authorized subject.
    Wiring to a real SCIM/SSO IdP is out of scope for this phase.
    """

    def sync(self) -> list[ConsentedIdentity]:
        raise NotImplementedError(
            "SCIM/SSO identity sync is design-only in this phase"
        )


# --------------------------------------------------------------------------- #
# Policy-as-code enforcement
# --------------------------------------------------------------------------- #
@runtime_checkable
class PolicyEnforcer(Protocol):
    """Turns a research recommendation into an enforced control-plane decision.

    The research core's :func:`signallock.policy.recommend` produces an
    auditable :class:`HardeningRecommendation`. An enforcer evaluates that
    recommendation against tenant-configured policy-as-code thresholds and
    returns a decision the surrounding system acts on.
    """

    def enforce(self, recommendation: HardeningRecommendation) -> str:
        """Return a decision: ``"enforce"``, ``"notify"``, or ``"block"``."""
        ...


class NoopPolicyEnforcer:
    """No-op :class:`PolicyEnforcer` — STUB.

    A real enforcer maps the recommendation's primary/supporting
    :class:`HardeningAction` and combined score onto tenant policy-as-code
    thresholds (e.g. "CRITICAL predictability -> block login until rotated;
    HIGH -> enforce MFA; MEDIUM -> notify"). Threshold configuration and the
    enforcement side effects are not built in this phase.
    """

    def enforce(self, recommendation: HardeningRecommendation) -> str:
        raise NotImplementedError(
            "policy-as-code enforcement is design-only in this phase"
        )


# --------------------------------------------------------------------------- #
# Audit + SIEM export
# --------------------------------------------------------------------------- #
@runtime_checkable
class AuditSink(Protocol):
    """Append-only record of control-plane events for compliance review."""

    def record(self, event: dict) -> None:
        """Persist one audit ``event`` (tamper-evident in a real deployment)."""
        ...


class NoopAuditSink:
    """No-op :class:`AuditSink` — STUB.

    A real sink writes immutable, tenant-partitioned audit rows (who scored whom,
    what recommendation, what enforcement decision) to durable storage. Not built
    in this phase.
    """

    def record(self, event: dict) -> None:
        raise NotImplementedError(
            "audit sink persistence is design-only in this phase"
        )


@runtime_checkable
class SiemExporter(Protocol):
    """Exports events to a customer SIEM as a single CEF / JSON line."""

    def export(self, event: dict) -> str:
        """Return the serialized SIEM line (CEF or JSON) for ``event``."""
        ...


class NoopSiemExporter:
    """No-op :class:`SiemExporter` — STUB.

    A real exporter serializes each audit event into the customer's SIEM format
    (ArcSight CEF or a JSON line for Splunk/Elastic) and ships it over the
    configured transport (syslog/HTTPS). Serialization and transport are not
    built in this phase.
    """

    def export(self, event: dict) -> str:
        raise NotImplementedError(
            "SIEM export is design-only in this phase"
        )


# --------------------------------------------------------------------------- #
# RBAC / API-key scopes (design)
# --------------------------------------------------------------------------- #
class Role(str, Enum):
    """Console roles for RBAC design."""

    ADMIN = "ADMIN"      # manage tenant config, roster, policy thresholds
    ANALYST = "ANALYST"  # run assessments, view recommendations
    AUDITOR = "AUDITOR"  # read-only access to audit trail and reports


class ApiKeyScope(str, Enum):
    """Scopes an issued API key may carry for least-privilege access."""

    READ = "READ"    # read assessments/reports
    SCORE = "SCORE"  # submit subjects for scoring
    ADMIN = "ADMIN"  # tenant/roster/policy administration
