# SignalLock v2 — Participant Intake (Option A pilot, `real-01` = you)

This is the operator runbook for the **consented real-participant** measurement
study, pilot N=1 with **you** as `real-01`. It turns your *real, existing* public
footprint into a consented snapshot and measures the exposure premium on study
passwords — no fabricated accounts, no ToS violations.

Companion: `docs/PERSONAS.md` (now used as the **intake field template** + the
**synthetic-control** set), `docs/RESEARCH_RUNBOOK.md` (pipeline), `docs/CONSENT_TEMPLATE.md`.

> **Safe-handling invariants (hold for every step):**
> - Plaintext passwords live **only** in a gitignored local file (`configs/passwords.local.json`); they are never committed and never printed to artifacts.
> - The pipeline persists only **bands/budgets**, never plaintext (matches `THREAT_MODEL.md`).
> - Collect only your **own** public data; use real accounts you own; nothing about third parties.

---

## Step 1 — Consent (self-consent for the pilot)

Fill `docs/CONSENT_TEMPLATE.md` for yourself and save it to the **gitignored**
path `configs/consent_records/real-01.json` (the `configs/consent_records/`
directory is gitignored; only the `.example` roster/snapshots are tracked).

Minimal consent record:
```json
{ "subject_id": "real-01", "granted_at": "2026-06-15", "is_dummy": false,
  "participant": "self", "scope": "public OSINT collection + study-password scoring",
  "withdrawal": "delete this file + the snapshot + any derived artifacts" }
```

## Step 2 — Roster entry

Create your real roster `configs/osint_roster.json` (gitignore it if the
`subject_id` could identify you; `real-01` is non-identifying, so it's safe to keep
local). `allowed_sources: []` permits all collectors.
```json
{ "subjects": [
  { "subject_id": "real-01", "consent_ref": "configs/consent_records/real-01.json",
    "granted_at": "2026-06-15", "is_dummy": false, "allowed_sources": [] }
] }
```

## Step 3 — Capture your real footprint into a snapshot

You harvest the **same fields** as in `docs/PERSONAS.md §3`, but from your *own*
real accounts. Two sub-paths:

### 3a. GitHub — automated live collection (the wired live source)
```bash
export GITHUB_TOKEN=ghp_xxx          # a personal access token (read-only is fine)
.venv/bin/python -m signallock --roster configs/osint_roster.json \
    collect-live --subject real-01 --github-user <your-github-handle> \
    --snapshots configs/snapshots
# -> writes configs/snapshots/real-01.json with your real NAME/ORG/LOCATION/
#    USERNAME/LANGUAGE/INTEREST observations, consent-gated.
```

### 3b. Social / professional — hand-authored, then merged
For LinkedIn, Mastodon, X, Instagram, etc. (your real accounts), **read your own
public profile** and add observations — these carry the high-value
`PERSONAL_TRIVIA` (pet/family/affiliation) the attacker mines. Author them in a
small JSON and merge:
```bash
# author configs/snapshots/real-01.extra.json with {"subject_id":"real-01","observations":[...]}
# then re-run collect-live with --merge to union GitHub + your manual observations
.venv/bin/python -m signallock --roster configs/osint_roster.json \
    collect-live --subject real-01 --github-user <your-handle> \
    --snapshots configs/snapshots --merge
```
(or just paste the manual observations directly into `configs/snapshots/real-01.json`.)

**Your intake table** — fill each row with *your real value*, then transcribe to an
observation `{source, attr_kind, value}` (see `PERSONAS.md §3` for the full map):

| Your attribute | Real value (yours) | From which of YOUR accounts | `source` / `attr_kind` |
|---|---|---|---|
| Full name | … | GitHub / LinkedIn | `CODE`/`NAME`, `PROFESSIONAL`/`NAME` |
| Username | … | GitHub | `CODE`/`USERNAME` |
| Employer / role | … | LinkedIn | `PROFESSIONAL`/`ORGANIZATION`,`ROLE_TITLE` |
| City | … | GitHub / LinkedIn | `CODE`/`LOCATION` |
| Pet name | … | Instagram / Mastodon | `SOCIAL`/`PET_NAME` |
| Family member | … | social | `SOCIAL`/`FAMILY_NAME` or `RELATIVE` |
| Significant year | … | social | `SOCIAL`/`SIGNIFICANT_YEAR` |
| Team / club | … | social / Reddit | `SOCIAL`/`AFFILIATION` |
| Hobbies | … | GitHub topics / web | `CODE`/`INTEREST`, `WEB`/`INTEREST` |
| Education | … | LinkedIn | `PROFESSIONAL`/`EDUCATION` |

Confirm capture worked:
```bash
.venv/bin/python -m signallock --roster configs/osint_roster.json \
    collect --subject real-01 --snapshots configs/snapshots   # exposure + token buckets
```

## Step 4 — Study passwords (gitignored, owner-set)

In **`configs/passwords.local.json`** (gitignored by `configs/*passwords*.json`)
list passwords *you choose for the study* — not your live secrets. Span the
contrast that proves the thesis:
```json
{ "real-01": [
  "<pet><year>",          /* OSINT-linked   -> expect HIGH/CRITICAL */
  "<team-name>",          /* affiliation    -> expect HIGH */
  "<unrelated-word><year>", /* structural twin, NOT in your OSINT -> expect LOW */
  "summer2021",           /* generic weak, non-personal -> expect MEDIUM */
  "<16-char random>"      /* control        -> expect LOW */
] }
```

## Step 5 — Measure

```bash
R=configs/osint_roster.json ; S=configs/snapshots ; P=configs/passwords.local.json

# Per-password (nothing persisted): the headline contrast on your real footprint
.venv/bin/python -m signallock --roster $R compare-baseline --subject real-01 \
    --password "<pet><year>" --snapshots $S      # expect positive premium, matched_category set
.venv/bin/python -m signallock --roster $R compare-baseline --subject real-01 \
    --password "<unrelated-word><year>" --snapshots $S   # expect ~0 premium, no match

# Full measurement (only bands/metrics persisted, never plaintext)
.venv/bin/python -m signallock --roster $R build-dataset --snapshots $S --passwords $P --out artifacts/study
.venv/bin/python -m signallock --roster $R evaluate --snapshots $S --passwords $P \
    --out artifacts/study_eval --seed 1 --figures
```

## Step 6 — Add synthetic controls (recommended)

Keep 2–3 personas from `docs/PERSONAS.md` (e.g. persona-01, persona-09) as
**synthetic** subjects alongside `real-01`. Reporting *real-participant premium vs
synthetic-control premium* shows the effect isn't a construction artifact — a
strength, not a weakness, in the writeup. Put their snapshots under the same
snapshots dir and their (clearly-fake) passwords in the gitignored passwords file.

---

## Pilot exit criteria
- [ ] `collect-live` produced `configs/snapshots/real-01.json` from your real GitHub.
- [ ] Manual social/professional observations merged in (pet/team/year present).
- [ ] `compare-baseline` shows **positive premium** for an OSINT-linked password and **~0** for its structural twin — on YOUR real footprint.
- [ ] `evaluate` emits AUROC/ECE/premium over `real-01` (+ controls); no plaintext in `artifacts/`.
- [ ] Consent record, snapshots, and `passwords.local.json` are all gitignored / local.
