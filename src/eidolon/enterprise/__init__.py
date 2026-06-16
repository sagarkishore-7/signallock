"""Enterprise control-plane interfaces and stubs (design-only this phase).

This package wraps the Eidolon research core with the interfaces an
enterprise deployment needs — tenant isolation, IdP sync, policy enforcement,
audit/SIEM export, and RBAC — as Protocols plus no-op reference implementations.
Nothing here is wired to real infrastructure yet; see
``docs/ENTERPRISE_ARCHITECTURE.md``.
"""

from __future__ import annotations

from .protocols import (
    ApiKeyScope,
    AuditSink,
    IdentitySync,
    NoopAuditSink,
    NoopIdentitySync,
    NoopPolicyEnforcer,
    NoopSiemExporter,
    PolicyEnforcer,
    Role,
    SiemExporter,
    TenantContext,
    tenant_scoped,
)

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
