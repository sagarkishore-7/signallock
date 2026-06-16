# Enterprise Architecture (Control Plane)

Eidolon's research core scores a single consented subject:

```
collect -> resolve -> exposure / predict -> policy.recommend
```

To operate that core as a multi-tenant enterprise service, it is wrapped by a
**control plane**. This document describes that trajectory and what ships now.

## Scope of this phase

**This phase ships interfaces + stubs only.** `src/eidolon/enterprise/`
contains `typing.Protocol` interfaces and no-op reference implementations whose
real methods raise `NotImplementedError`. There is:

- no tenant database or data-partitioning layer,
- no IdP (SSO/SCIM) integration,
- no audit store or SIEM transport,
- no admin UI or API-key issuance service.

The goal is to fix the seams — the boundaries between the proven research core
and the infrastructure that would productionize it — without prematurely
building that infrastructure.

## Control-plane trajectory

1. **Multi-tenant isolation.** Every roster, observation, assessment, and audit
   event is partitioned by tenant so one customer can never read or score
   another's subjects (row-level security or per-tenant schema). Represented by
   `TenantContext` and the `tenant_scoped(tenant_id)` context-manager stub.

2. **SSO/SCIM IdP sync -> consented roster.** The customer's directory (OIDC/SAML
   for SSO, SCIM for provisioning) is the source of truth for membership. Sync
   reconciles directory users against documented assessment consent and emits
   `ConsentedIdentity` records, preserving the core's consent gate.

3. **Policy-as-code enforcement.** Recommendations from the research core are
   evaluated against tenant-configured thresholds to produce an enforced
   decision (`enforce` / `notify` / `block`).

4. **Audit + SIEM export.** Every control-plane action is recorded to an
   append-only audit sink and can be exported to the customer SIEM as a CEF or
   JSON line (ArcSight / Splunk / Elastic).

5. **RBAC / API-key scopes.** Console access is role-based (`ADMIN`, `ANALYST`,
   `AUDITOR`); machine access uses scoped API keys (`READ`, `SCORE`, `ADMIN`)
   for least privilege.

## Protocol -> research-core mapping

| Protocol / type        | Wraps / depends on                                          |
| ---------------------- | ----------------------------------------------------------- |
| `TenantContext`, `tenant_scoped` | Partitions all core inputs/outputs per tenant     |
| `IdentitySync`         | Produces `eidolon.core.ConsentedIdentity` for the roster |
| `PolicyEnforcer`       | Wraps `eidolon.policy.recommend` -> `HardeningRecommendation`; reads `HardeningAction` / `RiskBand` from `eidolon.core` |
| `AuditSink`            | Records the recommendation + enforcement decision           |
| `SiemExporter`         | Serializes audit events for the customer SIEM               |
| `Role`, `ApiKeyScope`  | Gate who may invoke collect/score/admin operations          |

## Why stubs, not implementations

The research core is the defensible IP and is fully tested. The control plane is
conventional SaaS plumbing whose design (not its code) is what needs to be
agreed first. Shipping typed Protocols lets the core be reviewed against its
intended deployment shape while keeping this phase free of unproven
infrastructure.
