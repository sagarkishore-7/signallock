# Eidolon

### Your password's phantom double.

*Eidolon* (Greek **εἴδωλον**, *eidōlon*) — a phantom likeness of a person. A
targeted attacker assembles exactly such a likeness of you from public traces,
and passwords are often guessable from it. **Eidolon** is **defensive** security
research on **OSINT-calibrated password risk**: it builds that same public
likeness, mirrors the attacker's OSINT → cracking kill chain, and measures — then
hardens — the resulting risk. It never generates guess lists and never attacks
real accounts.

> **v2 — Adversary-Mirrored OSINT Defense.** Every collector is the structural
> mirror of one stage of an attacker's OSINT → cracking kill chain, run only
> against subjects who have given signed consent.

## The dual-layer idea

Eidolon keeps two variables separate and combines them only at the policy layer:

1. **Exposure** — how targetable an account is, from public OSINT (with
   *linkability* across platforms as a first-class signal).
2. **Password predictability** — how guessable a candidate password is *given* that
   exposure, labelled by a **bounded, consent-gated guess simulator** (which never
   emits or stores guess strings).

The headline metric is the **exposure premium**: the gap between a context-free
strength meter (zxcvbn) and Eidolon's context-aware estimate — i.e. the measurable
harm done by public OSINT.

## Ethics first

- **Consent is a hard gate.** Collection/scoring is refused for any subject not on a
  signed roster (`src/eidolon/core/identity.py`).
- **No fabricated accounts; no scraping ToS-hostile platforms.** Real data comes from
  **consenting participants' own accounts** (and the operator's own). See
  [`docs/OSINT_COLLECTION_PROTOCOL.md`](docs/OSINT_COLLECTION_PROTOCOL.md).
- **Derived data only.** Typed observations are kept (a pet name, a year) — never raw
  pages, **never plaintext passwords**. See [`docs/DATA_POLICY.md`](docs/DATA_POLICY.md).

## Taking part in the study

If you've been invited as a participant, start here — it takes ~20 minutes and your
details are returned privately, never committed to this repo:

1. [`docs/STUDY_INFORMATION_SHEET.md`](docs/STUDY_INFORMATION_SHEET.md) — what the study is.
2. [`docs/PARTICIPANT_GUIDE.md`](docs/PARTICIPANT_GUIDE.md) — how to take part.
3. [`docs/CONSENT_TEMPLATE.md`](docs/CONSENT_TEMPLATE.md) — consent form to sign.
4. [`docs/PARTICIPANT_INTAKE_FORM.md`](docs/PARTICIPANT_INTAKE_FORM.md) — the form to fill.

## Quick start (developers/operators)

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -e ".[ml,api,osint]"
.venv/bin/python -m unittest discover -t . -s tests -v        # 80+ tests, offline
```

The CLI mirrors the pipeline (runs against the clearly-fake example fixtures in
`configs/`):

```bash
R=configs/osint_roster.example.json ; S=configs/snapshots

.venv/bin/python -m eidolon mirror-table                                   # adversary-mirror registry
.venv/bin/python -m eidolon --roster $R collect --subject dummy-ghost --snapshots $S
.venv/bin/python -m eidolon --roster $R compare-baseline --subject dummy-ghost \
    --password rex2014 --snapshots $S        # pet+year: positive exposure premium, HIGH
.venv/bin/python -m eidolon --roster $R compare-baseline --subject dummy-ghost \
    --password fox2014 --snapshots $S        # structural twin not in OSINT: ~0 premium, LOW
.venv/bin/python -m eidolon --roster $R build-dataset --snapshots $S \
    --passwords configs/example_passwords.example.json --out artifacts/demo
.venv/bin/python -m eidolon --roster $R evaluate --snapshots $S \
    --passwords configs/example_passwords.example.json --out artifacts/demo_eval --figures
```

Live collection from a real (consented) GitHub account:

```bash
export GITHUB_TOKEN=ghp_...
.venv/bin/python -m eidolon --roster <roster> collect-live \
    --subject <id> --github-user <handle> --snapshots <dir>
```

Optional extras: `[ml]` (scikit-learn), `[api]` (FastAPI service), `[osint]` (httpx,
zxcvbn, bs4), `[demo]` (loopback-only attack/defense showcase).

## Repository layout

```
src/eidolon/
  core/      consent gate, typed evidence, subject, enums
  collect/   one collector per attacker source class (GitHub live; others snapshot)
  resolve/   observations -> subject (token buckets incl. personal-trivia)
  exposure/  surface x linkability model
  predict/   mangling -> simulator (labeler) -> zxcvbn baseline -> features -> learned -> premium
  policy/    exposure x predictability -> hardening action
  eval/      dataset, metrics (AUROC/ECE/ablations), expert packet, figures
  enterprise/ design-only Protocols + stubs
  api.py · cli.py
demo/        optional localhost attack/defense showcase
dashboard/   Next.js analyst UI
configs/     example roster + clearly-fake snapshots + example passwords
docs/        see the map below
```

## Documentation map

**Participant-facing:** `STUDY_INFORMATION_SHEET.md` · `PARTICIPANT_GUIDE.md` ·
`CONSENT_TEMPLATE.md` · `PARTICIPANT_INTAKE_FORM.md`

**Operator/researcher:** `RESEARCH_RUNBOOK.md` (pipeline) · `OPERATOR_PILOT.md` (the
N=1 self-pilot) · `PERSONAS.md` (synthetic controls + field reference)

**Ethics & design:** `THREAT_MODEL.md` · `DATA_POLICY.md` ·
`OSINT_COLLECTION_PROTOCOL.md` · `ADVERSARY_MIRROR.md` · `ENTERPRISE_ARCHITECTURE.md`

## License

Apache-2.0
