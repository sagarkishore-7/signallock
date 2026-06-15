"""Tests for the design-only enterprise control-plane stubs.

These assert the package imports cleanly, the RBAC enums carry the expected
members, and that every no-op reference implementation (and the tenant-scoping
context manager) clearly raises ``NotImplementedError`` — i.e. is unmistakably
not built in this phase.
"""

from __future__ import annotations

import unittest

import signallock.enterprise as ent
from signallock.enterprise import (
    ApiKeyScope,
    NoopAuditSink,
    NoopIdentitySync,
    NoopPolicyEnforcer,
    NoopSiemExporter,
    Role,
    TenantContext,
    tenant_scoped,
)


class EnterpriseImportTests(unittest.TestCase):
    def test_package_exports_all_names(self) -> None:
        for name in ent.__all__:
            self.assertTrue(hasattr(ent, name), f"missing export: {name}")

    def test_tenant_context_is_a_dataclass(self) -> None:
        ctx = TenantContext(tenant_id="t1", display_name="Tenant One")
        self.assertEqual(ctx.tenant_id, "t1")
        self.assertEqual(ctx.display_name, "Tenant One")


class RbacEnumTests(unittest.TestCase):
    def test_role_members(self) -> None:
        self.assertEqual(
            {r.name for r in Role}, {"ADMIN", "ANALYST", "AUDITOR"}
        )

    def test_api_key_scope_members(self) -> None:
        self.assertEqual(
            {s.name for s in ApiKeyScope}, {"READ", "SCORE", "ADMIN"}
        )


class StubsRaiseTests(unittest.TestCase):
    def test_tenant_scoped_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            with tenant_scoped("t1"):
                pass

    def test_identity_sync_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            NoopIdentitySync().sync()

    def test_policy_enforcer_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            NoopPolicyEnforcer().enforce(None)  # type: ignore[arg-type]

    def test_audit_sink_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            NoopAuditSink().record({})

    def test_siem_exporter_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            NoopSiemExporter().export({})


if __name__ == "__main__":
    unittest.main()
