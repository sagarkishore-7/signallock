# SignalLock Threat Model

## Objective

SignalLock is a defensive system for estimating targeted password risk and recommending authentication hardening actions. It is not an offensive guessing framework.

## Primary Security Question

Given ethically sourced public context about an account, how much additional password risk does that context create, and what defensive action should the organization take?

## Protected Assets

- enterprise user accounts
- candidate passwords evaluated in interactive mode
- public-profile snapshots or normalized public attributes
- policy thresholds and hardening decisions
- explanation outputs shown to analysts or end users

## Operating Modes

### Audit Mode

Purpose:

- rank account exposure,
- identify accounts that should receive stronger controls,
- produce explainable recommendations for security teams.

This mode should not require access to real passwords.

### Interactive Mode

Purpose:

- score a candidate password during password creation or password change,
- explain why it is risky under the user's public context,
- map the result to defensive actions such as warn, reject, or require MFA.

This mode should avoid storing plaintext passwords beyond the immediate scoring workflow.

## Adversary Model

SignalLock assumes an attacker who may have:

- access to public user information,
- access to role or organization context,
- knowledge of common password structure patterns,
- access to prior breach-derived aggregate password knowledge,
- limited online guessing opportunities.

SignalLock does not assume:

- system compromise,
- access to password hashes,
- privileged insider access to the organization's authentication backend,
- unrestricted brute-force capability.

## Defensive Boundaries

Allowed:

- estimating exposure risk from consented public context,
- labeling candidate-password risk via the bounded-budget guess simulator without
  emitting concrete guess strings,
- using aggregate breach structure priors to model likely risk classes,
- recommending hardening actions such as MFA or step-up authentication.

Disallowed:

- producing password lists or targeted guesses for real users,
- profiling unauthorized real individuals,
- collecting data in violation of platform terms or organizational policy,
- storing or exporting real plaintext passwords for later analysis.

## Trust Boundaries

### Trusted

- the local scoring workflow in interactive mode,
- consent-based datasets and fabricated dummy-account sources,
- policy configuration managed by authorized administrators,
- normalized schemas defined by the project.

### Less Trusted / External

- raw public web content,
- external public profile data,
- third-party organizational directories,
- user-provided free-text context.

External data should be normalized, minimized, and auditable before use.

## Risk Decomposition

The system must keep these risks separate:

### Exposure Risk

- how visible the user is,
- how rich their public attribute surface is,
- how likely they are to be targeted,
- how much attacker-relevant context is inferable.

### Password Predictability Risk

- how much a candidate password overlaps with public attributes,
- how much it follows common targeted structure patterns,
- how much easier it becomes to predict under limited online guess budgets.

### Policy Risk

- the combined hardening decision after exposure and password risk are evaluated separately.

## Risk Classes

The pipeline uses bounded-budget guess labels (`RiskBand` in
`src/signallock/core/enums.py`):

- `LOW`: not reached within the largest guess budget
- `MEDIUM`: contextual predictability with limited structural overlap; falls only at the largest budget
- `HIGH`: vulnerable within realistic targeted guess budgets
- `CRITICAL`: strong contextual overlap; falls within a handful of guesses, needs rejection or mandatory hardening

## Bounded Guess Budgets

The bounded-budget guess simulator (`predict/simulator.py`) labels each consented
owner password by the smallest budget (number of attempts) at which a
personalized candidate matches. The budgets are defined as the `Budget` enum in
`src/signallock/core/enums.py` and map to risk bands via `BUDGET_TO_BAND`:

| Budget | Attacker tier modeled | Band if reached |
|---|---|---|
| `B1` (1 attempt) | a single obvious contextual guess (pet, year) | CRITICAL |
| `B10` (10 attempts) | low-friction targeted online guessing, no lockout | CRITICAL |
| `B100` (100 attempts) | aggressive but still bounded online targeting | HIGH |
| `B1000` (1000 attempts) | rate-limited online / small targeted run | HIGH |
| `B10000` (10000 attempts) | offline targeted-dictionary run (CUPP/TarGuess scale) | MEDIUM |
| not reached | survives the largest budget | LOW |

Calibration is evaluated against these bounded budgets rather than against
unbounded offline cracking.

## Simulator Misuse Guards

The guess simulator is the research-grade "attack" — and is constrained so it
cannot become an attack tool. These guards are unit-tested:

- **Consent gate.** The simulator calls `require_consent(identity, roster)` first
  and refuses any non-roster subject with `ConsentError`.
- **Never emits guess strings.** It returns only the matched `RiskBand` and the
  matching template *category* — never a concrete candidate string, and it
  persists none.
- **Hard budget cap.** Enumeration is hard-capped at the top budget (`B10000`);
  it cannot run unbounded.

## Attack Demo — Loopback Only

The optional sandbox attack demo (`demo/`, separable and non-load-bearing) never
targets live third-party hosts:

- `demo/target_service.py` is a **local** auth service that binds localhost only
  and refuses non-loopback connections.
- `demo/run_attack.py` **hard-refuses any target host that is not loopback**
  (asserted in a test). It drives `predict/mangling.py` against the local
  sandbox only; no live-platform attack is ever performed.
- Dummy accounts on real platforms are OSINT *sources*, never attack *targets*.

## Threats SignalLock Tries to Reduce

- targeted online password guessing
- public-context-amplified password predictability
- poor prioritization of enterprise hardening actions
- generic strength-meter feedback that ignores attacker context

## Threats Out of Scope

- phishing detection
- malware defense
- offline hash-cracking resistance as the primary metric
- account takeover from session theft or token theft
- biometric or passkey analysis

## Misuse Resistance Principles

- expose risk scores, not candidate guess strings
- favor aggregate pattern features over reversible raw data
- keep internal context files and proposal drafts private when needed
- minimize retained public-profile text
- make policy actions explainable and reviewable

## Implementation Implications

The v2 pipeline supports:

- consented OSINT collection emitting typed `Observation`s (no raw scrape),
- explicit observation/subject and attribute schemas (`core/`),
- a clear split between exposure data and password-conditioned features,
- the bounded-budget guess simulator as the ground-truth labeler,
- the exposure-premium headline metric (context-free strength minus
  context-aware strength),
- CLI and offline workflows exercisable on the clearly-fake example roster and
  snapshot fixtures without requiring real enterprise data.

The retired v1 synthetic profile generation, preset experiments, and threshold
sweeps are no longer part of the threat surface.
