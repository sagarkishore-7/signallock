# SignalLock v2 — Adversary Mirror

SignalLock's organizing thesis is that **the defense is the structural mirror of
the attacker's OSINT to cracking kill chain**. Every collector reproduces one
stage of what a real adversary does, in the order they do it, so the
"defense vs offense" contribution is enforced by the architecture rather than
asserted in prose.

Each collector declares the attacker tool it reproduces via its `mirrors`
attribute, registered centrally in the collector registry (`collect/base.py`).
**This table is generated from code** via `collect.adversary_mirror_table()`, so
it stays in sync with the registered collectors; the version below is the
human-readable reference.

## The kill-chain mapping

| Attacker stage | Real tool | Signal harvested | SignalLock collector / component | Ethical mode |
|---|---|---|---|---|
| Username pivot | Maigret / Sherlock | account existence across sites | `UsernameEnumerator` (`username_enum.py`, `USERNAME_ENUM`) | HTTP existence checks, owned allowlist |
| Email pivot | Holehe / h8mail | accounts tied to an email | `EmailEnumerator` (`email_enum.py`, `EMAIL_ENUM`) | owned-allowlist only |
| Breach correlation | HIBP / COMB | breach membership + **structure priors only** | `BreachIntel` (`breach_intel.py`, `BREACH_INTEL`) | corpus stats, snapshot-backed, no cleartext for third parties |
| Footprint search | theHarvester / SpiderFoot | mentions, emails, subdomains | `FootprintSearch` (`footprint.py`, `FOOTPRINT_SEARCH`) | owned domains only |
| Professional | LinkedIn / company dir | role, seniority, tenure, org, education | `ProfessionalProfile` (`professional.py`, `PROFESSIONAL`) | **manual snapshot only** |
| Code | GitHub / GitLab API | usernames, languages, commit emails | `CodeProfile` (`code_profile.py`, `CODE`) | live API, owned/consented |
| Social / personal | X / IG / Reddit / Mastodon | pets, family, birthdays, teams, hobbies, geotags | `SocialProfile` (`social.py`, `SOCIAL`) | API where owned, else snapshot |
| Personal web | blogs / portfolios | bio / interests free text | `WebProfile` (`web_profile.py`, `WEB`) | owned URLs only |
| Data brokers / records | Spokeo / voter rolls | DOB, address, relatives, phone | `PublicRecords` (`public_records.py`, `PUBLIC_RECORDS`) | **gated manual snapshot only** |
| Snapshot ingest | (operator manual collection) | any typed observation from a gated source | `SnapshotCollector` (`snapshot.py`, `SNAPSHOT`) | operator-authored consented snapshot |
| Wordlist generation | CUPP / Mentalist / pydictor | personalized mangling templates | `predict/mangling.py` (mirrored in predict layer) | derived from consented tokens only |
| Targeted guess | TarGuess / hashcat / PCFG | guess rank within a bounded budget | `predict/simulator.py` (`TargetedRankEstimator`) | consented roster only; emits band + template category, never guess strings |

## Notes

- **The last two rows live in the predict layer, not in `collect/`.** The
  attacker's wordlist-generation stage (CUPP/Mentalist/pydictor) is mirrored by
  `predict/mangling.py`, which builds personalized guess templates from the
  consented subject's typed tokens. The attacker's targeted-guessing stage
  (TarGuess/hashcat/PCFG) is mirrored by `predict/simulator.py`, the
  bounded-budget guess simulator that reports the budget at which a consented
  owner password falls.
- **`mirrors` provenance.** Each `Observation` records the attacker tool it
  mirrors in its `mirrors` field (e.g. `maigret`, `holehe`, `hibp`, `cupp`), so
  the adversary-mirror view is reconstructable per-datum, not just per-collector.
- **ToS-hostile sources are documented, not scraped.** LinkedIn, public records,
  and breach cleartext appear in this table for the research narrative but are
  never auto-queried — they enter only via operator-authored consented snapshots
  (see `docs/OSINT_COLLECTION_PROTOCOL.md`).
- **Ethical max.** No live login attack is part of the research path. The only
  "attack" is the bounded-budget guess simulator against a consented password;
  the optional sandbox demo is loopback-only (see `docs/THREAT_MODEL.md`).

See `docs/ADVERSARY_MIRROR.md` references in `src/signallock/core/enums.py`
(`SourceClass`) for the source-class to attacker-tool comments that this table
expands on.
