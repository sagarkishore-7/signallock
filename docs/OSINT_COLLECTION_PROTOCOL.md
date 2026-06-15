# SignalLock v2 — OSINT Collection Protocol

This is the operating procedure for ethical OSINT collection in SignalLock v2.
SignalLock is a defensive research system: every collector is the structural
mirror of one stage of the attacker's OSINT to cracking kill chain
(see `docs/ADVERSARY_MIRROR.md`), run only against subjects who have signed
consent. This document defines *how* collection is allowed to happen so the
adversary-mirror spine never becomes an actual attack tool.

## 1. Consent first — the hard gate

Collection is refused for any subject who is not backed by a signed
`ConsentRecord` in the active `ConsentRoster`.

- The single ethical boundary is `require_consent(identity, roster, source=...)`
  in `src/signallock/core/identity.py`. Every collector and the guess simulator
  call it **before** touching a network source or a password. A subject who is
  not in the roster is refused with `ConsentError`.
- A `ConsentRecord` carries `subject_id`, `consent_ref` (the path/id of the
  signed consent artifact), `granted_at` (ISO date), `is_dummy`, and an optional
  `allowed_sources` allowlist. When `allowed_sources` is non-empty, only the
  named `SourceClass` collectors may run for that subject; an empty set means all
  sources are permitted.
- The signed consent artifact each `consent_ref` points at lives under
  `configs/consent_records/<subject_id>.json`, which is **gitignored and never
  committed** (see `docs/DATA_POLICY.md`). Only the clearly-fake example roster
  and snapshot fixtures are tracked.
- Subjects have a standing right to withdraw. On withdrawal the operator removes
  the subject from the roster, deletes the consent record and any derived
  Observations/Subject for that id. See `docs/CONSENT_TEMPLATE.md` for the
  withdrawal clause.

## 2. Dummy-account methodology

Dummy accounts are OSINT **sources**, never attack **targets**.

The operator creates dummy accounts on real platforms and seeds them with
realistic but entirely fabricated trivia, then harvests that consented material
to prove the OSINT to token to predictability chain on fully-controlled data.

Procedure:

1. **Create.** The operator registers a fresh account on a real platform under a
   research persona (e.g. `dummy-ghost`). The account belongs to the operator;
   no real third party is involved.
2. **Seed with fake trivia.** Populate the persona with realistic-looking but
   fabricated personal trivia of the kind a targeted attacker mines: a pet name,
   a sports team / affiliation, a birth/significant year, a name, an org, a role
   title. The seeded values are fake by construction (e.g. pet `Rex`, year
   `2014`, team `Riverside Rovers`).
3. **Roster.** Add the dummy-account handle to the consent roster with
   `is_dummy: true` (see `configs/osint_roster.example.json`). Dummy accounts are
   self-consented by the operator who created them.
4. **Collect as a source.** Run collectors against the dummy account exactly as
   against any consented subject. The harvested Observations exercise the full
   offline path and let the bounded-budget guess simulator demonstrate that a
   password like `rex2014` (pet + significant year) falls early.
5. **Never attack.** A dummy account is never the *target* of a login attack.
   The only "attack" in the research path is the bounded-budget guess simulator
   running against a consented owner password, and the optional sandbox demo,
   which is loopback-only.

This methodology is documented here for the research write-up so reviewers can
reproduce the OSINT to token to predictability chain on fabricated data.

## 3. Source handling — API/allowlist vs manual-snapshot-only

Each collector maps to one `SourceClass` in `src/signallock/core/enums.py`. The
ethical mode is fixed per source:

| SourceClass | Collector | Mode |
|---|---|---|
| `CODE` | `code_profile.py` | **Live API** (GitHub/GitLab via `httpx`), owned/consented |
| `SOCIAL` | `social.py` | Live **API where owned** (e.g. Mastodon), else snapshot |
| `USERNAME_ENUM` | `username_enum.py` | HTTP existence checks, owned allowlist |
| `EMAIL_ENUM` | `email_enum.py` | Owned-allowlist only |
| `FOOTPRINT_SEARCH` | `footprint.py` | Owned domains only |
| `WEB` | `web_profile.py` | Owned URLs only |
| `PROFESSIONAL` | `professional.py` | **Manual snapshot only** (LinkedIn / company dir) |
| `PUBLIC_RECORDS` | `public_records.py` | **Gated manual snapshot only** (data brokers / voter rolls) |
| `BREACH_INTEL` | `breach_intel.py` | **Snapshot-backed**: breach list + structure priors only, never cleartext for third parties |
| `SNAPSHOT` | `snapshot.py` | Operator-authored consented snapshot ingest |

**ToS-hostile or invasive sources are never auto-scraped.** LinkedIn, public
records, ToS-hostile social, and breach cleartext enter **only** via
operator-authored consented snapshots. The invasive collectors
(`breach_intel`, `public_records`) ship snapshot-backed with their live API path
stubbed and documented, never auto-querying third parties.

## 4. Retention — derived Observations only

Collectors emit typed `Observation` records, never a flattened profile and never
raw dumps.

- Persist only derived `Observation`s; **drop raw HTML/text** after extraction.
- An `Observation` (`src/signallock/core/evidence.py`) carries
  `subject_id`, `source` (`SourceClass`), `attr_kind` (`AttributeKind`), `value`,
  `confidence`, `collected_at`, `provenance`, and `mirrors` — and nothing else.
- The transient on-disk collection cache lives under `artifacts/osint_cache/`,
  which is gitignored.
- No raw PII enters the repository. See `docs/DATA_POLICY.md` for the full
  retention rule.

## 5. Authoring a snapshot JSON

For every manual/gated source, an operator authors a consented snapshot that the
`snapshot.py` loader (`load_snapshot`) replays through the same consent gate as
the live collectors.

Schema consumed by `src/signallock/collect/snapshot.py`:

```json
{
  "subject_id": "dummy-ghost",
  "observations": [
    {
      "source": "SOCIAL",
      "attr_kind": "PET_NAME",
      "value": "Rex",
      "confidence": 0.9,
      "mirrors": "cupp",
      "provenance": "snapshot:ig-fake"
    }
  ]
}
```

Field rules:

- `subject_id` must match a roster entry; the snapshot collector filters to that
  id and the consent gate refuses non-roster subjects.
- `source` is the exact string name of a `SourceClass` enum member; `attr_kind`
  is the exact string name of an `AttributeKind` enum member
  (`src/signallock/core/enums.py`).
- `confidence` is in `[0, 1]`; `collected_at` and `provenance` are optional and
  default to sensible values in the loader.
- `mirrors` names the attacker tool the datum mirrors (e.g. `cupp`, `maigret`,
  `hibp`) for the adversary-mirror report.
- Use only **derived, typed** facts — no raw scraped text, no cleartext
  passwords. A `BREACH` observation carries only the breach *name*; a
  `STRUCTURE_PRIOR` carries only a structural habit (e.g. `word+4digits`), never
  a real password.

See `configs/snapshots/dummy-ghost.json` and its siblings for clearly-fake
worked examples.
