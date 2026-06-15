# Participant Intake Form

Fill this in a **private** copy and return it to the researcher per
[`PARTICIPANT_GUIDE.md`](PARTICIPANT_GUIDE.md). **Do not commit it to this repo.**

- Only enter details that are **already public** about you. Leave anything blank you
  don't want to share — partial answers are fine.
- The **study passwords** at the end must be **throwaway** — *never* a real or reused
  password.

Read [`STUDY_INFORMATION_SHEET.md`](STUDY_INFORMATION_SHEET.md) and sign
[`CONSENT_TEMPLATE.md`](CONSENT_TEMPLATE.md) first.

---

## Part A — About your public footprint

**Which of these public accounts do you have?** (tick) — give the handle/URL only if
it's public.

- `[ ]` GitHub — handle/URL: `__________`
- `[ ]` LinkedIn — public URL: `__________`
- `[ ]` Mastodon — handle: `__________`
- `[ ]` X / Twitter — handle: `__________`
- `[ ]` Instagram — handle: `__________`
- `[ ]` Reddit — handle: `__________`
- `[ ]` Personal site / blog — URL: `__________`
- `[ ]` Other: `__________`

## Part B — Public attributes (fill what's public about you)

| # | Field | Your value (leave blank if not public) |
|---|---|---|
| 1 | First name (as shown publicly) | `__________` |
| 2 | Surname (if public) | `__________` |
| 3 | A shortened/preferred name you use publicly | `__________` |
| 4 | Employer / organisation (if public) | `__________` |
| 5 | Job title / role (if public) | `__________` |
| 6 | City / location (if public) | `__________` |
| 7 | School / university (if public) | `__________` |
| 8 | A year that's visible about you (grad year, start year) | `__________` |
| 9 | Pet name(s) you've posted publicly | `__________` |
| 10 | A family member's name you've posted publicly | `__________` |
| 11 | A sports team / club / fandom you publicly follow | `__________` |
| 12 | Hobbies / interests visible on your profiles | `__________` |
| 13 | A username/handle you reuse across sites | `__________` |
| 14 | Programming languages (if you have public code) | `__________` |

> Skip anything that isn't genuinely public or that you'd rather not share. The more
> that's accurate-to-public, the better the measurement — but it's your choice.

## Part C — Study passwords (THROWAWAY ONLY)

Invent **5–6 passwords for the study**. **Do not use any password you actually use.**
The point of the experiment is the *contrast* below, so please include a mix:

1. One that **uses some of your public details above** (e.g. a pet name + a year):
   `__________`
2. Another using **different public details** (e.g. your team, or employer + year):
   `__________`
3. A **look-alike** of #1 but using a word that is **NOT** about you — same shape,
   unrelated word (e.g. if #1 is `comet2009`, give something like `falcon2009`):
   `__________`
4. A generic weak password with **no personal connection** (e.g. `summer2021`):
   `__________`
5. A **strong random** password (e.g. from a password manager), ~16 chars:
   `__________`
6. *(optional)* one more of your choosing: `__________`

✔️ Confirm: `[ ]` None of the above is a password I actually use anywhere.

## Part D — Confirmations

- `[ ]` I have read the Participant Information Sheet.
- `[ ]` I have completed and signed the consent form.
- `[ ]` The public details above are things already visible about me online.
- `[ ]` The study passwords are throwaway and not used by me anywhere.

**Non-identifying id (assigned by researcher):** `participant-____`
**Date (ISO):** `__________`

---

<!-- OPERATOR NOTE (not for participants): map each Part B row to a snapshot
observation {source, attr_kind} per docs/PERSONAS.md §3, then build the snapshot
JSON and run the pipeline (docs/RESEARCH_RUNBOOK.md). Field→attr_kind: 1/2→NAME,
3→PREFERRED_NAME, 4→ORGANIZATION, 5→ROLE_TITLE, 6→LOCATION, 7→EDUCATION,
8→SIGNIFICANT_YEAR/TENURE_YEAR, 9→PET_NAME, 10→FAMILY_NAME, 11→AFFILIATION,
12→INTEREST, 13→USERNAME, 14→LANGUAGE. Study passwords go in the gitignored
configs/passwords.local.json; only bands/scores are persisted. -->
