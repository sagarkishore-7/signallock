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

- estimating exposure risk from organization-approved or consented public context,
- estimating candidate-password risk without generating concrete guesses,
- using synthetic, anonymized, or aggregate statistics to model likely risk classes,
- recommending hardening actions such as MFA or step-up authentication.

Disallowed:

- producing password lists or targeted guesses for real users,
- profiling unauthorized real individuals,
- collecting data in violation of platform terms or organizational policy,
- storing or exporting real plaintext passwords for later analysis.

## Trust Boundaries

### Trusted

- the local scoring workflow in interactive mode,
- organization-approved synthetic or consent-based datasets,
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

Early implementation should use online-guess-oriented labels:

- `LOW`: unlikely to fall within a low-budget targeted online attack window
- `MEDIUM`: some contextual predictability but limited structural overlap
- `HIGH`: likely to be vulnerable within realistic targeted online guess budgets
- `CRITICAL`: strong contextual overlap and likely need for rejection or mandatory hardening

## Initial Guess-Budget Assumptions

These are working assumptions for Phase 1 and can be revised later:

- `Budget-1`: first-guess obvious contextual matches
- `Budget-10`: low-friction targeted online attempts
- `Budget-100`: aggressive but still bounded online targeting

The project should evaluate calibration against these budgets rather than against unbounded offline cracking.

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

## Phase 1 Implementation Implications

The first code should support:

- synthetic profile generation
- explicit profile and attribute schemas
- a clear split between exposure data and password-conditioned features
- CLI workflows that help test the model design without requiring real enterprise data

Current implementation status:

- synthetic profile generation is implemented,
- baseline exposure scoring is implemented,
- baseline candidate-password scoring is implemented,
- baseline policy mapping is implemented,
- calibration and deployment tuning remain future work.
