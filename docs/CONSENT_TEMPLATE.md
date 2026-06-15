# SignalLock v2 — Research Consent Form Template

This is a reusable, plain-language consent form a research subject — or the
operator of a dummy account — signs before SignalLock collects any OSINT or
assesses any password for that subject. A signed copy is stored as the consent
artifact referenced by `consent_ref` in the consent roster
(`configs/osint_roster.example.json`) and lives under
`configs/consent_records/<subject_id>.json`, which is **gitignored and never
committed**.

The signed record enables the hard consent gate
(`require_consent` in `src/signallock/core/identity.py`): SignalLock refuses to
collect on or score any subject who is not on the roster.

---

## Template

**SignalLock OSINT & Password-Risk Research — Consent Form**

**Subject id:** `__________________`
(the label used in the roster; for a dummy account this is the persona id)

**1. Who I am.** I am the person, or the operator of the account(s), identified
below, and I am authorized to grant this consent.

**2. What I authorize.** I authorize the SignalLock research operator to collect
publicly available OSINT about the following handles/emails/domains, and to
assess the password(s) I provide, for defensive password-risk research only:

- Named handles / usernames: `__________________`
- Email addresses: `__________________`
- Domains / personal sites: `__________________`

**3. Sources.** Collection may run against the following source classes only
(matching `SourceClass` in `src/signallock/core/enums.py`); any source not
listed here is excluded:

- `[ ]` SOCIAL  `[ ]` CODE  `[ ]` USERNAME_ENUM  `[ ]` EMAIL_ENUM
- `[ ]` FOOTPRINT_SEARCH  `[ ]` WEB  `[ ]` PROFESSIONAL  `[ ]` PUBLIC_RECORDS
- `[ ]` BREACH_INTEL (breach names + structure priors only, never cleartext)
- `[ ]` SNAPSHOT (operator-authored consented snapshot)

If no boxes are checked, all sources are permitted (an empty `allowed_sources`).

**4. What is stored.** Only derived, typed observations are retained (a pet name,
a year, an org — never raw scraped pages, never my plaintext password). Raw
source text is dropped after extraction. See `docs/DATA_POLICY.md`.

**5. How it is used.** My data is used only to estimate exposure and password
predictability and to demonstrate the OSINT to predictability research chain.
SignalLock never emits concrete guess strings and never attacks any live
third-party account.

**6. Dummy account (if applicable).** `[ ]` This subject is an operator-created
**dummy account** (`is_dummy: true`) seeded with fabricated trivia and used only
as an OSINT *source*, never as an attack *target*.

**7. Withdrawal rights.** I may withdraw consent at any time, in writing, with no
penalty. On withdrawal the operator removes me from the roster and deletes my
consent record and all derived observations within a reasonable period.

**8. Retention.** Derived observations are retained only for the duration of the
study and deleted on withdrawal or study end.

**Signature:** `__________________`  **Date (ISO):** `__________`

**Operator countersignature:** `__________________`  **Date:** `__________`

---

## Filled EXAMPLE — `dummy-ghost` (CLEARLY FAKE)

This example corresponds to the fabricated research persona `dummy-ghost` in
`configs/osint_roster.example.json`. Every value is fake by construction.

**SignalLock OSINT & Password-Risk Research — Consent Form**

**Subject id:** `dummy-ghost`

**1. Who I am.** I am the SignalLock research operator and the creator of the
dummy account(s) below. There is no real third party.

**2. What I authorize.** Collection on, and assessment of, the following:

- Named handles / usernames: `ghostdev` (fabricated dummy account)
- Email addresses: `ghost.persona@example.invalid`
- Domains / personal sites: *(none)*

**3. Sources.** Permitted source classes:

- `[x]` SOCIAL  `[x]` CODE  `[x]` SNAPSHOT
- (all others excluded — matches `allowed_sources: ["SOCIAL","CODE","SNAPSHOT"]`)

**4. What is stored.** Only derived observations (e.g. pet `Rex`, year `2014`,
team `Riverside Rovers`, org `Fabricated Labs Inc`). No raw pages, no plaintext
passwords.

**5. How it is used.** To exercise the offline OSINT to predictability pipeline
and demonstrate that a contextual password such as `rex2014` falls within a small
guess budget.

**6. Dummy account.** `[x]` This subject is an operator-created dummy account
(`is_dummy: true`), seeded with fabricated trivia, used only as an OSINT source.

**7. Withdrawal rights.** The operator may retire `dummy-ghost` at any time by
removing it from the roster and deleting `configs/consent_records/dummy-ghost.json`
and all derived observations.

**8. Retention.** Retained only for the duration of the research.

**Signature:** `Research Operator (dummy-ghost)`  **Date (ISO):** `2026-01-15`

**Operator countersignature:** `Research Operator`  **Date:** `2026-01-15`
