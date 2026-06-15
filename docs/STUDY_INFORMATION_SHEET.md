# Participant Information Sheet — SignalLock OSINT & Password-Risk Study

*Please read this before deciding to take part. Version 1.0 · 2026-06-15.*

## What is this study?

SignalLock is **defensive** security research. We are studying a simple question:

> Does the information people already share publicly online (a pet's name, a
> favourite team, a graduation year, an employer) make their passwords easier for
> a targeted attacker to guess — and can a defender measure that risk?

The goal is to **help defenders warn users and harden authentication**, *not* to
build an attack tool. SignalLock never produces guess lists and never attacks any
real account.

## Why have I been asked?

You have been invited because you maintain ordinary public online profiles
(e.g. GitHub, LinkedIn, a social account, a personal site). Taking part is
**entirely voluntary**.

## What does taking part involve? (~20 minutes)

1. Read this sheet and, if happy, **complete the consent form** (`docs/CONSENT_TEMPLATE.md`).
2. **Fill the intake form** (`docs/PARTICIPANT_INTAKE_FORM.md`) with public details
   you *already share openly* — the kind of thing anyone could find by looking you up.
3. **Choose 5–6 throwaway "study passwords"** following the form's guidance.
   **These must NOT be passwords you actually use anywhere.**
4. Return the completed forms **privately** to the researcher (see Contact). Do
   **not** post them in the public repository.

## What data do you collect — and what do you NOT collect?

**We collect** only *derived, typed facts* from information you choose to disclose
that is already public (a first name, a pet name, a year, an employer) and the
**throwaway study passwords** you invent for the study.

**We do NOT collect:** your real or reused passwords; private/non-public
information; raw web pages or screenshots; anything about other people. We do not
scrape any platform — you tell us what is public about you.

## How is my data protected?

- Only **derived attributes** are kept — never raw pages, **never a plaintext
  password** (the analysis stores only a risk band/score). See `docs/DATA_POLICY.md`.
- You are referred to by a **non-identifying id** (e.g. `participant-03`); your real
  handle appears only in a consent record that is **never published**.
- Results are reported **in aggregate**; no individual is identified.
- A built-in consent gate refuses to process anyone not on the signed roster.

## What are the risks and benefits?

**Risks are minimal.** The study passwords are throwaway and are never used against
any real account; the public details are things you already expose. **Benefits:**
you contribute to defensive password research. There is no payment unless the
researcher states otherwise in writing.

## Voluntariness and withdrawal

Participation is voluntary. You may **withdraw at any time, without giving a reason
and without penalty**. On withdrawal we delete your consent record and all derived
data within a reasonable period (`docs/OSINT_COLLECTION_PROTOCOL.md` §1).

## Confidentiality

Your identity is separated from your data. Only the researcher can link the
non-identifying id back to you, via the offline consent record.

## Contact and concerns

- **Researcher:** SignalLock research operator — `contact@matrixsociallabs.com`
- If the study runs under an institution, its ethics/IRB approval reference and an
  independent contact for complaints will be added here: `[institution / IRB ref]`.

By completing the consent form you confirm you have read and understood this sheet.
