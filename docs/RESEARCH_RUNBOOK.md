# SignalLock v2 — Research Runbook (operator guide)

This is the end-to-end guide for turning the v2 prototype into a real,
consented-OSINT measurement study: what exists, what's left to build, and
**step-by-step dummy-account creation + data entry for each platform**.

Companion docs: `OSINT_COLLECTION_PROTOCOL.md` (ethics/consent rules),
`CONSENT_TEMPLATE.md` (consent form), `ADVERSARY_MIRROR.md` (which attacker tool
each collector mirrors), `THREAT_MODEL.md` (budgets), `DATA_POLICY.md` (retention).

---

## 1. What is implemented today (v2, merged to `main`)

| Layer | Module(s) | Status |
|---|---|---|
| **Consent spine** | `core/identity.py` (`require_consent` hard gate), `core/errors.py` | ✅ every collector + simulator gate on consent |
| **Typed evidence model** | `core/evidence.py` (`Observation`), `core/subject.py` (`Subject` + token buckets incl. PERSONAL_TRIVIA), `core/enums.py` | ✅ |
| **Collectors (adversary mirrors)** | `collect/` — `code_profile` (GitHub, **live API**), `social`, `web_profile`, `username_enum`, `email_enum`, `footprint`, `professional`, `public_records`, `breach_intel`, `snapshot` | ✅ classes + mocked tests. ⚠️ Only `snapshot` is wired into the CLI; live collectors aren't CLI-exposed yet |
| **Entity resolution** | `resolve/entity.py`, `resolve/tokens.py` | ✅ Observations → Subject with typed token buckets |
| **Exposure model** | `exposure/model.py` — surface sub-scores × **linkability multiplier**; axes: discoverability, linkability, professional visibility, personal-trivia richness, breach exposure, temporal | ✅ |
| **Predictability** | `predict/` — `mangling` (CUPP/TarGuess-style templates), `simulator` (bounded-budget ground-truth labeler, consent-gated, no guess strings persisted), `baseline` (zxcvbn), `features`, `learned` (sklearn budget-bucket predictor → AUROC/ECE), `premium` (exposure premium) | ✅ |
| **Policy** | `policy/engine.py` — exposure × predictability → hardening action | ✅ |
| **Evaluation** | `eval/dataset.py`, `eval/metrics.py` (AUROC, ECE, ablations, premium), `eval/expert.py`, `eval/figures.py` | ✅ |
| **API** | `api.py` — `/subjects`, `/score/exposure`, `/score/predictability`, `/recommend`, `/compare-baseline`, `/healthz` | ✅ |
| **Dashboard** | `dashboard/` (Next.js) | ⚠️ shell present; attacker-mirror/premium views need wiring (verify) |
| **Enterprise** | `enterprise/protocols.py` — Protocols + stubs (design only) | ✅ by design |
| **Demo** | `demo/` — loopback-only attack/defense showcase, `[demo]` extra | ✅ |
| **CLI** | `signallock {collect,score,compare-baseline,build-dataset,evaluate,mirror-table,demo}` | ✅ (snapshot-driven) |

**Verified offline (fake fixtures):** 78 tests pass; `evaluate` gives honest
non-1.0 numbers (acc 0.857 / AUROC 0.878 / ECE 0.164 vs baseline 0.143); the
`rex2014` vs `fox2014` premium demonstration works (+2.94 vs +0.44).

---

## 2. Engineering gaps to close before / alongside real data

Priority order:

1. **Wire live collectors into the CLI.** Add `signallock collect --live` (or a
   `--sources` flag) that runs the registered collectors (`CodeProfile`,
   `social` Mastodon, `web_profile`, `username_enum`) for a subject's seeds and
   writes the resulting `Observation`s to a snapshot file. Today the CLI only
   replays snapshots; the GitHub collector works but must be called in a script.
2. **README refresh.** `README.md` is still entirely v1 (documents removed
   commands like `train-model`, `generate-profiles`, `run-preset`). Rewrite the
   Quick Start + command reference for the v2 CLI.
3. **`PROJECT_STATUS.md` / `FEATURE_SCHEMA.md` refresh** to the v2 schema.
4. **Scale the roster** to a study-sized N (see §6) and add a real (non-example)
   gitignored roster + consent records + passwords file.
5. **Dashboard verification** — confirm the attacker-mirror + exposure-premium
   panels render against `/subjects` and `/compare-baseline`.

---

## 3. The data model you must produce (so the pipeline runs)

For each consented subject you need **three artifacts**:

### (a) A roster entry — `configs/osint_roster.json` (gitignored for real use)
```json
{ "subjects": [
  { "subject_id": "dummy-otter", "consent_ref": "configs/consent_records/dummy-otter.json",
    "granted_at": "2026-06-20", "is_dummy": true,
    "allowed_sources": ["CODE","SOCIAL","PROFESSIONAL","WEB","SNAPSHOT"] }
] }
```
`allowed_sources` (optional) restricts which collectors may run; empty = all.
Valid `SourceClass` names: `USERNAME_ENUM, EMAIL_ENUM, BREACH_INTEL,
FOOTPRINT_SEARCH, PROFESSIONAL, CODE, SOCIAL, WEB, PUBLIC_RECORDS, SNAPSHOT`.

> **Roster privacy:** the roster itself is **not** gitignored (only consent
> records, `configs/*passwords*.json`, and `artifacts/` are). A roster of
> `dummy-*` personas holds no PII, so it's safe to track. For **real
> volunteers**, either use non-identifying `subject_id`s (e.g. `volunteer-01`,
> keeping the real handle only inside the gitignored consent record) **or** add
> your real roster filename to `.gitignore`. Real per-person seeds
> (email/username) belong in the gitignored consent record, never in a tracked file.

### (b) A signed consent record — `configs/consent_records/<id>.json` (**gitignored, never committed**)
Use `docs/CONSENT_TEMPLATE.md`. For your own dummy accounts you are the consenting
party (`is_dummy: true`). For real volunteers, they sign it.

### (c) A snapshot of harvested attributes — `<snapshots-dir>/<id>.json`
This is the heart of the data. Schema (consumed by `collect/snapshot.py`):
```json
{ "subject_id": "dummy-otter",
  "observations": [
    {"source":"SOCIAL","attr_kind":"PET_NAME","value":"Otter","confidence":0.9,
     "mirrors":"cupp","provenance":"snapshot:ig-fake"}
  ] }
```
- `source` = exact `SourceClass` name. `attr_kind` = exact `AttributeKind` name.
- `confidence` ∈ [0,1]. `mirrors` = the attacker tool (`cupp`,`maigret`,`hibp`,…).
- **Derived facts only** — no raw scraped text, no cleartext passwords. A `BREACH`
  obs carries only the breach *name*; a `STRUCTURE_PRIOR` only a habit like
  `word+4digits`.

### `AttributeKind` → token bucket (what drives risk)
| Bucket | AttributeKinds |
|---|---|
| **personal_trivia** (highest value) | `PET_NAME`, `FAMILY_NAME`, `RELATIVE`, `AFFILIATION` |
| temporal | `TENURE_YEAR`, `SIGNIFICANT_YEAR`, `DATE_OF_BIRTH` |
| name | `NAME`, `PREFERRED_NAME` |
| organization | `ORGANIZATION`, `ROLE_TITLE`, `EDUCATION` |
| identity | `USERNAME`, `EMAIL`, `LANGUAGE` |
| location | `LOCATION`, `ADDRESS` |
| interest | `INTEREST` |
| structure_prior | `STRUCTURE_PRIOR` |
| (signal only) | `PLATFORM_PRESENCE`, `PHONE`, `BREACH` |

### Budget → risk band (how the simulator labels a password)
`B1/B10 → CRITICAL`, `B100/B1000 → HIGH`, `B10000 → MEDIUM`, not reached → `LOW`.

---

## 4. Dummy-account creation playbook — per platform

**Golden rules:** (1) Accounts are OSINT *sources you own*, never attack targets.
(2) Seed only **fabricated** trivia (fake pet, fake team, fake year) — never real
people's data. (3) ToS-hostile platforms are **never auto-scraped**: you read your
own seeded profile and hand-author the snapshot JSON.

For each persona, pick a **theme** so the trivia is internally consistent and so
some passwords are OSINT-derivable (e.g. pet `Otter`, year `2016`, team
`Lakeside Otters`, employer `Northwind Co`).

### Platform A — GitHub  → `SourceClass: CODE`  (live API OK)
- **Where:** https://github.com/signup
- **Fill in:** profile **Name** (→ `NAME`), **Bio**, **Company** (→ `ORGANIZATION`),
  **Location** (→ `LOCATION`); create 2–3 public repos, set a primary **language**
  (→ `LANGUAGE`) and a few **topics**/repo names (→ `INTEREST`). Username (→ `USERNAME`).
- **Collect:** this is the one source automatable today via the `CodeProfile`
  collector (`GITHUB_TOKEN` + the username seed). Until the CLI `--live` flag
  exists, run it from a short script and dump to a snapshot, or just transcribe
  the public fields into the snapshot JSON.
- **Mirrors:** `github-api` / `gitrecon`.

### Platform B — Mastodon → `SourceClass: SOCIAL`  (live API where you own the account)
- **Where:** pick an instance, e.g. https://mastodon.social/auth/sign_up
- **Fill in:** display **Name**, **Bio** (drop a pet name / hobby / hometown),
  a few posts mentioning the **pet** (→ `PET_NAME`), **team** (→ `AFFILIATION`),
  **interests** (→ `INTEREST`).
- **Collect:** Mastodon has a clean public API; live collection is feasible via
  the `social` collector. Otherwise snapshot.
- **Mirrors:** `sherlock` / social-OSINT.

### Platform C — Instagram → `SourceClass: SOCIAL`  (**manual snapshot only** — ToS)
- **Where:** https://www.instagram.com/ (web or app signup)
- **Fill in:** a profile with a **pet photo + caption naming the pet**
  (→ `PET_NAME`), a **sports team / fandom** in bio (→ `AFFILIATION`), **city**
  (→ `LOCATION`), maybe a **family member tag** (→ `FAMILY_NAME`/`RELATIVE`).
- **Collect:** **do not scrape.** Open your own profile, read the values, and
  hand-write the snapshot observations.
- **Mirrors:** `cupp` (the trivia an attacker mines for a wordlist).

### Platform D — X/Twitter → `SourceClass: SOCIAL`  (manual snapshot only)
- **Where:** https://x.com/i/flow/signup
- **Fill in:** bio + a few posts with **interests**, **affiliation**, **location**.
- **Collect:** manual snapshot (API is paywalled; don't scrape).

### Platform E — Reddit → `SourceClass: SOCIAL`  (manual snapshot only)
- **Where:** https://www.reddit.com/register/
- **Fill in:** subscribe/post in subs that reveal **interests**/**affiliations**
  (e.g. a team sub → `AFFILIATION`).
- **Collect:** manual snapshot.

### Platform F — LinkedIn → `SourceClass: PROFESSIONAL`  (**manual snapshot only** — ToS)
- **Where:** https://www.linkedin.com/signup
- **Fill in:** **Name**, **Headline/Role** (→ `ROLE_TITLE`), **Company**
  (→ `ORGANIZATION`), **Education** (→ `EDUCATION`), start year (→ `TENURE_YEAR`),
  **Location** (→ `LOCATION`).
- **Collect:** **never automate.** Read your own profile, hand-author the snapshot.
- **Mirrors:** `linkedin-snapshot`.

### Platform G — Personal site / blog → `SourceClass: WEB`  (owned URL)
- **Where:** free via GitHub Pages (https://pages.github.com/) or any host.
- **Fill in:** an "about me" with **bio / interests / hometown**.
- **Collect:** `web_profile` collector on your own URL (or snapshot).

### Platform H — Public records / data brokers → `SourceClass: PUBLIC_RECORDS`  (gated, fabricated only)
- **Do NOT** query real broker sites for real DOB/address/relatives.
- For dummy personas, **fabricate** `DATE_OF_BIRTH`, `ADDRESS`, `RELATIVE` and put
  them straight into the snapshot (this models the broker stage ethically).

### Platform I — Breach intel → `SourceClass: BREACH_INTEL`  (snapshot, structure only)
- Add a fabricated `BREACH` (breach *name* only) and a `STRUCTURE_PRIOR` such as
  `word+4digits` — **never** a real or cleartext password.
- Models "this person reuses a `pet+year` shape" without storing a secret.

---

## 5. What trivia to seed (the high-signal checklist per persona)

Seed enough that some passwords are derivable and some twins are not:
- **Pet name** (`PET_NAME`) — e.g. `Otter`
- **Significant year** (`SIGNIFICANT_YEAR`/`DATE_OF_BIRTH`) — e.g. `2016`
- **Sports team / fandom** (`AFFILIATION`) — e.g. `Lakeside Otters`
- **Family member** (`FAMILY_NAME`/`RELATIVE`) — e.g. `Maya`
- **Employer + role + start year** (`ORGANIZATION`/`ROLE_TITLE`/`TENURE_YEAR`)
- **City** (`LOCATION`), **education** (`EDUCATION`), **hobbies** (`INTEREST`)
- **Username + email** (`USERNAME`/`EMAIL`)

---

## 6. Owner-set passwords (the consented "real password" layer)

For each persona, author a passwords map (mirror `configs/example_passwords.example.json`)
in a **gitignored** file, e.g. `configs/passwords.local.json`:
```json
{ "dummy-otter": [
  "otter2016",            /* OSINT-linked weak: pet+year  -> should fall fast (CRITICAL/HIGH) */
  "Otter2016!",           /* same trivia, dressed up      -> still derivable */
  "lakesideotters",       /* affiliation                  -> derivable */
  "seal2016",             /* STRUCTURAL TWIN: same shape, NOT in OSINT -> should survive (LOW) */
  "mountainpaddlers",     /* twin of the team name        -> survives */
  "Tg7$qP2!vLn8wKpd"      /* strong random control        -> survives */
] }
```
The twin vs OSINT-linked contrast is the core of the thesis (zxcvbn can't tell
`otter2016` from `seal2016`; SignalLock can). Real consented volunteers may instead
submit passwords they actually chose for their own consented accounts.

**Study size target:** ~15–40 personas × 6–8 passwords ≈ 100–300 labeled rows for a
credible small-N measurement study. Start with 8–10 fully-seeded personas, then grow.
Optionally recruit a few consenting colleagues (signed consent) for external validity.

---

## 7. Running the study (commands)

```bash
cd "/Users/sagarkishore/Cysec Tools/SignalLock"
R=configs/osint_roster.json          # your real (gitignored) roster
S=configs/snapshots                  # your snapshot dir (real personas)
P=configs/passwords.local.json       # your gitignored owner-set passwords

# Per-subject sanity
.venv/bin/python -m signallock --roster $R collect --subject dummy-otter --snapshots $S
.venv/bin/python -m signallock --roster $R compare-baseline --subject dummy-otter \
    --password otter2016 --snapshots $S      # expect HIGH + positive premium
.venv/bin/python -m signallock --roster $R compare-baseline --subject dummy-otter \
    --password seal2016 --snapshots $S       # expect LOW + ~0 premium (the twin)

# Full study
.venv/bin/python -m signallock --roster $R build-dataset --snapshots $S --passwords $P --out artifacts/study
.venv/bin/python -m signallock --roster $R evaluate --snapshots $S --passwords $P \
    --out artifacts/study_eval --seed 1 --figures
```
Outputs (gitignored under `artifacts/`): labeled dataset CSV, AUROC/ECE, baseline
delta, exposure-premium distribution, per-axis ablations, SVG figures.

Then: expert-actionability study via `eval/expert.py`, and write up RQ1 (premium),
RQ3 (ablations), RQ4 (expert agreement).

---

## 8. Ethics checklist (every run)
- [ ] Subject is in the roster with a signed consent record (`is_dummy` for your accounts).
- [ ] `configs/consent_records/`, `configs/passwords.local.json`, `artifacts/` are gitignored (verified).
- [ ] Real volunteers use non-identifying `subject_id`s, or the roster file itself is gitignored.
- [ ] Snapshots contain only **derived, fabricated** facts — no raw scraped text, no cleartext passwords.
- [ ] ToS-hostile sources (LinkedIn/IG/X/records) entered **only** by manual snapshot.
- [ ] No real third party profiled; dummy accounts are sources, never attack targets.
