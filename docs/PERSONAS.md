# SignalLock v2 — Research Personas (reference dataset)

Companion to `docs/RESEARCH_RUNBOOK.md`. This file specifies the **fabricated
research personas** for the consented-OSINT study: how many, what each one is,
which platforms they live on, **exactly what to type in each field**, how that
field is captured as OSINT, and the owner-set passwords with their expected
ground-truth bands.

> **Ethics (non-negotiable).** Every persona is 100% fabricated. You (the
> operator) create and own every account; each is `is_dummy: true` and
> self-consented. Accounts are OSINT **sources**, never attack **targets**. Seed
> only invented trivia — never a real person's data. ToS-hostile platforms
> (LinkedIn, Instagram, X, Reddit) are **read by you and hand-transcribed** into
> snapshot JSON — never auto-scraped. Per-account login emails: use aliases you
> control, e.g. `yourmailbox+maraellison@gmail.com`.

---

## 1. How many personas, and why

**Core set: 12 personas.** They are designed as a matrix so the study can answer
its research questions, not as 12 random people:

- **Exposure tier** (drives RQ3 / the exposure model): 4 HIGH, 4 MEDIUM, 4 LOW —
  varying platform breadth and **linkability** (HIGH personas reuse one username
  across every platform so the resolver cross-links them; LOW personas appear on
  a single platform).
- **Role seniority** spans IC → C-suite (professional-visibility axis).
- **Personal-trivia richness** spans rich (pet+family+team+dates public) → sparse.
- **Password-derivation bucket** is varied across personas (pet+year, family+year,
  team/affiliation, org+year, location) so the ablations have signal in every
  `PERSONAL_TRIVIA`/temporal sub-category.

12 personas × 6 owner-set passwords = **72 labeled rows** minimum; add more
passwords per persona to reach ~150–200. This is a defensible **small-N
feasibility/measurement** study — state it as such, and optionally augment with a
few signed-consent colleagues for external validity.

**Phased rollout** (account creation is slow and platforms flag fakes):
- **Pilot (week 1):** persona-01, -05, -09, -12 (one per exposure tier + GitHub-only) — proves the whole pipeline on real data.
- **Core (weeks 2–3):** the remaining 8.
- **Optional expansion:** clone the pattern to 20–40 by adding personas/passwords.

---

## 2. Master matrix

| id | Name (fabricated) | Role / Seniority | Org / City | Exposure | Linkability (shared username) | Platforms | Primary derivation |
|---|---|---|---|---|---|---|---|
| persona-01 | Mara Ellison | VP Engineering / VP | Northwind Robotics, Seattle | **HIGH** | `maraellison` everywhere | GitHub, LinkedIn, X, Instagram, Mastodon, Reddit, Web | pet+year `comet2009` |
| persona-02 | Dev Saraf | CISO / C_SUITE | FinClast, London | **HIGH** | `devsaraf` everywhere | GitHub, LinkedIn, X, Mastodon, Web, Breach | family+year `arjun2012` |
| persona-03 | Bianca Rossi | Director Marketing / DIRECTOR | Lumio Travel, Milan | **HIGH** | `biancarossi` everywhere | Instagram, X, LinkedIn, Reddit, Web | pet+year `pixel2015` |
| persona-04 | Theo Andersen | Engineering Manager / MANAGER | Bitfjord, Oslo | **HIGH** | `theoandersen` everywhere | GitHub, LinkedIn, Mastodon, Reddit, Web | pet `loki2010` |
| persona-05 | Priya Nair | Software Engineer / IC | Cobalt Health, Bangalore | MEDIUM | `priyanair-dev` (GitHub/Reddit) | GitHub, LinkedIn, Reddit | pet+year `mango2018` |
| persona-06 | Owen Fletcher | Product Manager / MANAGER | Drift Audio, Austin | MEDIUM | `owenfletcher` (X/IG) | LinkedIn, X, Instagram | team `hillcountryhawks` |
| persona-07 | Sofia Marchetti | Security Analyst / IC | Vantage Bank, Toronto | MEDIUM | `sofiamarchetti` (GitHub/Mastodon) | GitHub, Mastodon, LinkedIn | pet+year `nova2016` |
| persona-08 | Daniel Kim | Finance Manager / MANAGER | Helios Energy, Singapore | MEDIUM | `danielkim-sg` (X/Web) | LinkedIn, X, Web | family+year `hana2013` |
| persona-09 | Lena Hofer | Accountant / IC | Graustein GmbH, Vienna | LOW | none (single platform) | LinkedIn only | pet `schnitzel` |
| persona-10 | Marcus Bell | Warehouse Supervisor / IC | Cargolink, Manchester | LOW | none | Instagram only | team `mosssiderovers` |
| persona-11 | Aiko Tanaka | Junior Designer / IC | Tsuki Studio, Osaka | LOW | `aikodraws` (IG/Web) | Instagram, Web | pet `mochi` |
| persona-12 | Sam Okoro | Developer / IC | Greenfield Apps, Lagos | LOW | `samokoro` (GitHub) | GitHub only | pet+year `zuri2019` |

---

## 3. OSINT capture model (how a field becomes a feature)

Each value you type on a platform is transcribed into one snapshot `Observation`
`{source, attr_kind, value}`, resolved into a token bucket, and consumed by the
exposure + predictability layers:

| Platform | SourceClass | Field you fill → `attr_kind` | Token bucket |
|---|---|---|---|
| GitHub | `CODE` | Name→`NAME`, Company→`ORGANIZATION`, Location→`LOCATION`, username→`USERNAME`, repo language→`LANGUAGE`, repo topic→`INTEREST` | name/org/location/identity/interest |
| Mastodon/X/Instagram/Reddit | `SOCIAL` | pet→`PET_NAME`, team/club→`AFFILIATION`, family→`FAMILY_NAME`/`RELATIVE`, year→`SIGNIFICANT_YEAR`, city→`LOCATION`, hobby→`INTEREST`, display name→`NAME` | **personal_trivia** / temporal / location / interest / name |
| LinkedIn | `PROFESSIONAL` | Name→`NAME`, Headline→`ROLE_TITLE`, Company→`ORGANIZATION`, School→`EDUCATION`, start year→`TENURE_YEAR`, Location→`LOCATION` | name/org/temporal/location |
| Personal site | `WEB` | About→`INTEREST`, name→`NAME` | interest/name |
| (fabricated) | `PUBLIC_RECORDS` | DOB→`DATE_OF_BIRTH`, address→`ADDRESS`, relative→`RELATIVE` | temporal/location/personal_trivia |
| (fabricated) | `BREACH_INTEL` | breach name→`BREACH`, habit→`STRUCTURE_PRIOR` | (signal) / structure_prior |

**Linkability:** reusing the *same username* across `CODE`+`SOCIAL`+`WEB` is what
lets the resolver co-resolve a subject across ≥2 platforms and raises the
exposure linkability multiplier — that's why HIGH personas share a handle and LOW
personas don't.

---

## 4. Per-persona specifications

Each block gives the **attribute card** (what to enter where + the snapshot
mapping) and the **owner-set passwords** with the expected simulator band.
Expected bands: pet/family/team/org tokens that ARE in OSINT → reachable within
budget (HIGH/CRITICAL); structural twins NOT in OSINT → survive (LOW); generic
weak non-personal → MEDIUM; random → LOW.

### persona-01 — Mara Ellison  (HIGH exposure, VP)
Username everywhere: **maraellison**. Email: `+maraellison`.
Trivia theme: dog **Comet**, daughter **Lila**, wedding year **2009**, fan club **Cascade Surge**, hometown **Seattle**, MIT 2006, hobby trail running.

| Attribute | Value | Enter on (platform → field) | Snapshot `source`/`attr_kind` |
|---|---|---|---|
| Name | Mara Ellison | GitHub Name; LinkedIn Name; socials display name | CODE/NAME, PROFESSIONAL/NAME |
| Username | maraellison | all platforms | CODE/USERNAME |
| Org | Northwind Robotics | GitHub Company; LinkedIn Company | CODE/ORGANIZATION, PROFESSIONAL/ORGANIZATION |
| Role | VP of Engineering | LinkedIn Headline | PROFESSIONAL/ROLE_TITLE |
| Tenure year | 2019 | LinkedIn start year | PROFESSIONAL/TENURE_YEAR |
| Education | MIT | LinkedIn School | PROFESSIONAL/EDUCATION |
| Location | Seattle | GitHub/LinkedIn Location; IG bio | CODE/LOCATION |
| Pet | Comet | Instagram caption; Mastodon bio | SOCIAL/PET_NAME |
| Family | Lila | Instagram tag; X post | SOCIAL/FAMILY_NAME |
| Sig. year | 2009 | Instagram "anniversary" post | SOCIAL/SIGNIFICANT_YEAR |
| Affiliation | Cascade Surge | X bio; Reddit (team sub) | SOCIAL/AFFILIATION |
| Interest | trail running | GitHub repo topic; Web about | CODE/INTEREST, WEB/INTEREST |
| Language | Python | GitHub repo primary language | CODE/LANGUAGE |

**Passwords** (`configs/passwords.local.json` → `"persona-01": [...]`):
`comet2009` (pet+year → **CRITICAL/HIGH**), `Comet2009!` (dressed → **HIGH**),
`cascadesurge` (affiliation → **HIGH**), `falcon2009` (twin, not in OSINT → **LOW**),
`summer2021` (generic weak → **MEDIUM**), `7rT$q9Lm!2pXvز` *(use any 16-char random)* (**LOW**).

### persona-02 — Dev Saraf  (HIGH exposure, CISO)
Username everywhere: **devsaraf**. Trivia: cat **Tiger**, son **Arjun**, year **2012**, club **Thames Wanderers**, London, LSE, hobby chess. Has a fabricated breach habit.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Dev Saraf | GitHub/LinkedIn/socials | CODE/NAME, PROFESSIONAL/NAME |
| Org | FinClast | GitHub Company; LinkedIn | CODE/ORGANIZATION |
| Role | Chief Information Security Officer | LinkedIn Headline | PROFESSIONAL/ROLE_TITLE |
| Education | LSE | LinkedIn School | PROFESSIONAL/EDUCATION |
| Location | London | GitHub/LinkedIn | CODE/LOCATION |
| Pet | Tiger | Mastodon bio | SOCIAL/PET_NAME |
| Family | Arjun | X post | SOCIAL/FAMILY_NAME |
| Sig. year | 2012 | X post | SOCIAL/SIGNIFICANT_YEAR |
| Affiliation | Thames Wanderers | X bio | SOCIAL/AFFILIATION |
| Interest | chess | Web about; GitHub topic | WEB/INTEREST |
| Breach (fab) | OldForum-2019 | (fabricated) | BREACH_INTEL/BREACH |
| Structure prior | word+4digits | (fabricated) | BREACH_INTEL/STRUCTURE_PRIOR |

**Passwords:** `arjun2012` (family+year → **CRITICAL/HIGH**), `Tiger2012` (pet+year → **HIGH**),
`thameswanderers` (affiliation → **HIGH**), `mason2012` (twin → **LOW**),
`password1` (generic weak → **MEDIUM/HIGH** via zxcvbn), random-16 (**LOW**).

### persona-03 — Bianca Rossi  (HIGH exposure, Director)
Username everywhere: **biancarossi**. Trivia: dog **Pixel**, partner **Marco**, anniversary **2015**, club **Navigli FC**, Milan, hobby photography.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Bianca Rossi | IG/X/LinkedIn/Web | SOCIAL/NAME, PROFESSIONAL/NAME |
| Org / Role | Lumio Travel / Director of Marketing | LinkedIn | PROFESSIONAL/ORGANIZATION, ROLE_TITLE |
| Location | Milan | LinkedIn; IG bio | PROFESSIONAL/LOCATION |
| Pet | Pixel | Instagram caption | SOCIAL/PET_NAME |
| Partner | Marco | Instagram tag | SOCIAL/RELATIVE |
| Sig. year | 2015 | Instagram post | SOCIAL/SIGNIFICANT_YEAR |
| Affiliation | Navigli FC | X bio; Reddit | SOCIAL/AFFILIATION |
| Interest | photography | Web/blog; IG bio | WEB/INTEREST |

**Passwords:** `pixel2015` (pet+year → **CRITICAL/HIGH**), `Marco2015!` (partner+year → **HIGH**),
`naviglifc` (affiliation → **HIGH**), `prism2015` (twin → **LOW**), `welcome2018` (generic → **MEDIUM**), random-16 (**LOW**).

### persona-04 — Theo Andersen  (HIGH exposure, Manager)
Username everywhere: **theoandersen**. Trivia: husky **Loki**, daughter **Freya**, NTNU **2010**, club **Fjordline United**, Oslo, hobby skiing.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Theo Andersen | GitHub/LinkedIn/Mastodon/Web | CODE/NAME |
| Org / Role | Bitfjord / Engineering Manager | GitHub Company; LinkedIn | CODE/ORGANIZATION, PROFESSIONAL/ROLE_TITLE |
| Education | NTNU | LinkedIn | PROFESSIONAL/EDUCATION |
| Location | Oslo | GitHub/LinkedIn | CODE/LOCATION |
| Pet | Loki | Mastodon bio; Reddit | SOCIAL/PET_NAME |
| Family | Freya | Mastodon post | SOCIAL/FAMILY_NAME |
| Grad year | 2010 | LinkedIn | PROFESSIONAL/TENURE_YEAR |
| Affiliation | Fjordline United | Reddit team sub | SOCIAL/AFFILIATION |
| Language | Go | GitHub repo language | CODE/LANGUAGE |

**Passwords:** `loki2010` (pet+year → **CRITICAL/HIGH**), `Bitfjord2010` (org+year → **HIGH**),
`fjordlineunited` (affiliation → **HIGH**), `bear2010` (twin → **LOW**), `qwerty123` (generic → **MEDIUM/HIGH**), random-16 (**LOW**).

### persona-05 — Priya Nair  (MEDIUM, IC)
Username: **priyanair-dev** (GitHub/Reddit). Trivia: parrot **Mango**, sibling **Kiran**, grad **2018**, Bangalore, hobby cycling.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Priya Nair | GitHub/LinkedIn | CODE/NAME |
| Org / Role | Cobalt Health / Software Engineer | GitHub Company; LinkedIn | CODE/ORGANIZATION, PROFESSIONAL/ROLE_TITLE |
| Grad year | 2018 | LinkedIn | PROFESSIONAL/TENURE_YEAR |
| Location | Bangalore | GitHub/LinkedIn | CODE/LOCATION |
| Pet | Mango | Reddit post | SOCIAL/PET_NAME |
| Sibling | Kiran | Reddit post | SOCIAL/RELATIVE |
| Interest | cycling | GitHub topic | CODE/INTEREST |
| Language | JavaScript | GitHub repo language | CODE/LANGUAGE |

**Passwords:** `mango2018` (pet+year → **CRITICAL/HIGH**), `Kiran2018` (sibling+year → **HIGH**),
`cobalt2018` (org+year → **HIGH**), `peach2018` (twin → **LOW**), `iloveyou` (generic → **MEDIUM/HIGH**), random-16 (**LOW**).

### persona-06 — Owen Fletcher  (MEDIUM, Manager)
Username: **owenfletcher** (X/IG). Trivia: dog **Banjo**, partner **Sam**, club **Hill Country Hawks**, Austin, hobby running.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Owen Fletcher | LinkedIn/X/IG | PROFESSIONAL/NAME |
| Org / Role | Drift Audio / Product Manager | LinkedIn | PROFESSIONAL/ORGANIZATION, ROLE_TITLE |
| Location | Austin | LinkedIn; IG bio | PROFESSIONAL/LOCATION |
| Pet | Banjo | Instagram caption | SOCIAL/PET_NAME |
| Partner | Sam | Instagram tag | SOCIAL/RELATIVE |
| Affiliation | Hill Country Hawks | X bio | SOCIAL/AFFILIATION |
| Interest | running | X bio | SOCIAL/INTEREST |

**Passwords:** `hillcountryhawks` (affiliation → **HIGH**), `banjo123` (pet+seq → **HIGH**),
`Banjo2020` (pet+year → **HIGH**), `condor99` (twin → **LOW**), `letmein` (generic → **MEDIUM/HIGH**), random-16 (**LOW**).

### persona-07 — Sofia Marchetti  (MEDIUM, IC)
Username: **sofiamarchetti** (GitHub/Mastodon). Trivia: cat **Nova**, grad **2016**, Toronto, hobby climbing.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Sofia Marchetti | GitHub/LinkedIn/Mastodon | CODE/NAME |
| Org / Role | Vantage Bank / Security Analyst | GitHub Company; LinkedIn | CODE/ORGANIZATION, PROFESSIONAL/ROLE_TITLE |
| Grad year | 2016 | LinkedIn | PROFESSIONAL/TENURE_YEAR |
| Location | Toronto | GitHub | CODE/LOCATION |
| Pet | Nova | Mastodon bio | SOCIAL/PET_NAME |
| Interest | climbing | GitHub topic; Mastodon | CODE/INTEREST |
| Language | Python | GitHub repo language | CODE/LANGUAGE |

**Passwords:** `nova2016` (pet+year → **CRITICAL/HIGH**), `Nova!2016` (dressed → **HIGH**),
`vantage2016` (org+year → **HIGH**), `vega2016` (twin → **LOW**), `sunshine` (generic → **MEDIUM**), random-16 (**LOW**).

### persona-08 — Daniel Kim  (MEDIUM, Manager)
Username: **danielkim-sg** (X/Web). Trivia: daughter **Hana**, year **2013**, Singapore, hobby golf.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Daniel Kim | LinkedIn/X/Web | PROFESSIONAL/NAME |
| Org / Role | Helios Energy / Finance Manager | LinkedIn | PROFESSIONAL/ORGANIZATION, ROLE_TITLE |
| Location | Singapore | LinkedIn | PROFESSIONAL/LOCATION |
| Family | Hana | X post | SOCIAL/FAMILY_NAME |
| Sig. year | 2013 | X post | SOCIAL/SIGNIFICANT_YEAR |
| Interest | golf | Web about | WEB/INTEREST |

**Passwords:** `hana2013` (family+year → **CRITICAL/HIGH**), `Hana_2013` (dressed → **HIGH**),
`helios2013` (org+year → **HIGH**), `mira2013` (twin → **LOW**), `123456789` (generic → **HIGH** via zxcvbn), random-16 (**LOW**).

### persona-09 — Lena Hofer  (LOW, IC; single platform)
No shared username. Trivia: dog **Schnitzel**, Vienna. **LinkedIn only** — thin footprint.

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Lena Hofer | LinkedIn | PROFESSIONAL/NAME |
| Org / Role | Graustein GmbH / Accountant | LinkedIn | PROFESSIONAL/ORGANIZATION, ROLE_TITLE |
| Location | Vienna | LinkedIn | PROFESSIONAL/LOCATION |
| Pet | Schnitzel | (only if you choose to expose; else omit) | SOCIAL/PET_NAME *(optional)* |

**Passwords:** `schnitzel1` (pet → **HIGH** *if pet exposed*, else **MEDIUM**),
`Graustein2020` (org+year → **MEDIUM/HIGH**), `vienna2020` (location+year → **MEDIUM**),
`strudel1` (twin → **LOW**), `qwerty` (generic → **HIGH** via zxcvbn), random-16 (**LOW**).
*(persona-09 tests that LOW exposure yields fewer derivable hits — a key negative control.)*

### persona-10 — Marcus Bell  (LOW, IC; single platform)
No shared username. Trivia: club **Moss Side Rovers**, Manchester. **Instagram only.**

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Marcus Bell | Instagram display | SOCIAL/NAME |
| Affiliation | Moss Side Rovers | Instagram bio | SOCIAL/AFFILIATION |
| Location | Manchester | Instagram bio | SOCIAL/LOCATION |
| Interest | football | Instagram bio | SOCIAL/INTEREST |

**Passwords:** `mosssiderovers` (affiliation → **HIGH**), `manchester1` (location → **MEDIUM**),
`rovers2019` (affiliation+year → **HIGH**), `eaglesnest` (twin → **LOW**), `football` (generic → **MEDIUM**), random-16 (**LOW**).

### persona-11 — Aiko Tanaka  (LOW, IC)
Username: **aikodraws** (IG/Web). Trivia: cat **Mochi**, Osaka, hobby illustration. **Instagram + portfolio.**

| Attribute | Value | Enter on | source/attr_kind |
|---|---|---|---|
| Name | Aiko Tanaka | Instagram/Web | SOCIAL/NAME, WEB/NAME |
| Pet | Mochi | Instagram caption | SOCIAL/PET_NAME |
| Location | Osaka | Instagram bio | SOCIAL/LOCATION |
| Interest | illustration | Web portfolio about | WEB/INTEREST |
| Username | aikodraws | IG + portfolio URL | SOCIAL/USERNAME |

**Passwords:** `mochi123` (pet+seq → **HIGH**), `Mochi2021` (pet+year → **HIGH**),
`aikodraws` (username → **HIGH**), `udon123` (twin → **LOW**), `abc123` (generic → **HIGH** via zxcvbn), random-16 (**LOW**).

### persona-12 — Sam Okoro  (LOW, IC; GitHub-only — the live-collect pilot)
Username: **samokoro** (GitHub). Trivia: dog **Zuri**, grad **2019**, Lagos, language Java. **GitHub only** — use this to pilot the live `CodeProfile` collector.

| Attribute | Value | Enter on (GitHub) | source/attr_kind |
|---|---|---|---|
| Name | Sam Okoro | Profile Name | CODE/NAME |
| Username | samokoro | handle | CODE/USERNAME |
| Org | Greenfield Apps | Profile Company | CODE/ORGANIZATION |
| Location | Lagos | Profile Location | CODE/LOCATION |
| Pet | Zuri | repo name `zuri-bot` / README *(or snapshot)* | SOCIAL/PET_NAME *(via snapshot)* |
| Grad year | 2019 | bio | SOCIAL/SIGNIFICANT_YEAR *(via snapshot)* |
| Language | Java | repo primary language | CODE/LANGUAGE |
| Interest | android | repo topic | CODE/INTEREST |

**Passwords:** `zuri2019` (pet+year → **CRITICAL/HIGH**), `Zuri_2019` (dressed → **HIGH**),
`greenfield19` (org+year → **HIGH**), `kano2019` (twin → **LOW**), `password123` (generic → **HIGH** via zxcvbn), random-16 (**LOW**).

---

## 5. Worked snapshot JSON (persona-01) — template for all

Drop one file per persona under your snapshots dir (e.g. `configs/snapshots/persona-01.json`).
Every other persona converts mechanically from its table above (one observation
per row, `value` lowercased is fine; `confidence` ~0.8–0.95; `mirrors` = `cupp`
for trivia, `maigret` for username, `linkedin-snapshot` for professional,
`github-api` for code).

```json
{
  "subject_id": "persona-01",
  "observations": [
    {"source":"CODE","attr_kind":"USERNAME","value":"maraellison","confidence":0.95,"mirrors":"maigret","provenance":"snapshot:github"},
    {"source":"CODE","attr_kind":"NAME","value":"Mara Ellison","confidence":0.9,"mirrors":"github-api","provenance":"snapshot:github"},
    {"source":"CODE","attr_kind":"ORGANIZATION","value":"Northwind Robotics","confidence":0.85,"mirrors":"github-api","provenance":"snapshot:github"},
    {"source":"CODE","attr_kind":"LOCATION","value":"Seattle","confidence":0.8,"mirrors":"github-api","provenance":"snapshot:github"},
    {"source":"CODE","attr_kind":"LANGUAGE","value":"Python","confidence":0.7,"mirrors":"github-api","provenance":"snapshot:github"},
    {"source":"PROFESSIONAL","attr_kind":"ROLE_TITLE","value":"VP of Engineering","confidence":0.9,"mirrors":"linkedin-snapshot","provenance":"snapshot:linkedin"},
    {"source":"PROFESSIONAL","attr_kind":"EDUCATION","value":"MIT","confidence":0.85,"mirrors":"linkedin-snapshot","provenance":"snapshot:linkedin"},
    {"source":"PROFESSIONAL","attr_kind":"TENURE_YEAR","value":"2019","confidence":0.85,"mirrors":"linkedin-snapshot","provenance":"snapshot:linkedin"},
    {"source":"SOCIAL","attr_kind":"PET_NAME","value":"Comet","confidence":0.9,"mirrors":"cupp","provenance":"snapshot:instagram"},
    {"source":"SOCIAL","attr_kind":"FAMILY_NAME","value":"Lila","confidence":0.85,"mirrors":"cupp","provenance":"snapshot:instagram"},
    {"source":"SOCIAL","attr_kind":"SIGNIFICANT_YEAR","value":"2009","confidence":0.85,"mirrors":"cupp","provenance":"snapshot:instagram"},
    {"source":"SOCIAL","attr_kind":"AFFILIATION","value":"Cascade Surge","confidence":0.8,"mirrors":"cupp","provenance":"snapshot:x"},
    {"source":"WEB","attr_kind":"INTEREST","value":"trail running","confidence":0.7,"mirrors":"web","provenance":"snapshot:website"}
  ]
}
```

---

## 6. Roster + how this drives the study

Real roster (track if `dummy-*`/non-identifying ids; see runbook §3 note),
`configs/osint_roster.json`:

```json
{ "subjects": [
  {"subject_id":"persona-01","consent_ref":"configs/consent_records/persona-01.json","granted_at":"2026-06-20","is_dummy":true,"allowed_sources":[]},
  {"subject_id":"persona-02","consent_ref":"configs/consent_records/persona-02.json","granted_at":"2026-06-20","is_dummy":true,"allowed_sources":[]}
  /* … persona-03 … persona-12, allowed_sources: [] = all permitted … */
] }
```

**What the study then measures:**
- **RQ1 / exposure premium:** for each persona, OSINT-linked passwords (e.g.
  `comet2009`) should show a large premium (zxcvbn can't see the trivia);
  structural twins (`falcon2009`) should show ~0 — proving real OSINT, not
  password shape, drives the risk.
- **RQ3 / exposure model:** HIGH personas (broad + cross-linked) should score
  higher exposure and have more derivable passwords than LOW personas
  (persona-09/10/11/12 are the negative controls); ablating personal-trivia vs
  professional axes shows which footprint matters most.
- **RQ4 / actionability:** feed the per-persona recommendations + explanations to
  security pros via `eval/expert.py`.

Run with the commands in `docs/RESEARCH_RUNBOOK.md` §7.
```
```
