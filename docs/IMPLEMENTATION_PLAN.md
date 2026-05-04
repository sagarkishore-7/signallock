# SignalLock Implementation Plan

## Goal

Build a defensive, research-grade prototype that separates:

- `Exposure Risk`: account targetability from OSINT,
- `Password Predictability Risk`: candidate-password risk conditioned on exposure,
- `Hardening Action`: authentication or training recommendations based on calibrated risk.

## Product Modes

### 1. Audit Mode

For authorized enterprise security teams.

Inputs:

- approved employee roster,
- organization-controlled public profile snapshots or URLs,
- policy configuration.

Outputs:

- exposure heatmaps by department and role,
- prioritized hardening recommendations,
- explainable per-user risk reports.

### 2. Interactive Mode

For password creation or password change.

Inputs:

- candidate password,
- local or organization-approved public attribute vector,
- policy configuration.

Outputs:

- exposure-aware password risk score,
- explanation of major contributing features,
- recommendations such as revise password, accept, or require MFA.

## System Decomposition

### A. Data Governance Layer

Responsibilities:

- define allowed data sources,
- enforce synthetic or consent-based evaluation,
- keep raw OSINT handling auditable,
- define retention and deletion policies.

Deliverables:

- `docs/DATA_POLICY.md`,
- source allowlist,
- ethics checklist template.

### B. OSINT Exposure Engine

Responsibilities:

- ingest structured public profile data,
- extract names, aliases, titles, dates, organizations, locations, usernames, and platform presence,
- derive exposure-oriented features without storing more raw text than necessary.

Candidate technologies:

- `requests`, `BeautifulSoup`, `trafilatura`,
- `spaCy`,
- `pydantic` for normalized schemas.

Deliverables:

- `ProfileRecord` schema,
- `AttributeVector` schema,
- feature extraction tests on synthetic profiles.

### C. Candidate Password Risk Engine

Responsibilities:

- accept a candidate password,
- compute generic strength features,
- compute attribute-conditioned overlap and transformability features,
- predict targeted online-risk class.

Baseline models:

- `zxcvbn`-style generic meter baseline,
- lightweight statistical baseline,
- gradient-boosted tree or calibrated neural classifier.

Important constraint:

- the engine should assess risk, not emit actual guesses.

Deliverables:

- password feature extractor,
- conditional risk model,
- calibration evaluation notebook.

### D. Policy and Hardening Engine

Responsibilities:

- combine exposure and password scores,
- map results to actions,
- support organization-specific thresholds.

Actions:

- allow,
- warn,
- reject,
- require stronger password,
- enforce MFA,
- require step-up authentication,
- prioritize awareness training.

Deliverables:

- `RiskPolicy` schema,
- default policy profiles,
- simulation results for threshold tuning.

### E. Explainability Layer

Responsibilities:

- explain exposure score,
- explain password risk score,
- explain final policy action.

Candidate technologies:

- SHAP for model explanation,
- template-based natural language explanations,
- simple visual summaries.

Deliverables:

- per-user explanation JSON,
- analyst report renderer,
- interactive explanation component.

### F. Interface Layer

#### CLI

Initial development entrypoint for:

- running batch audits,
- scoring candidate passwords locally,
- exporting reports.

#### Dashboard

Later-stage analyst interface with:

- org-level heatmaps,
- user drill-downs,
- export and audit logging.

Candidate technologies:

- FastAPI backend,
- React frontend,
- Chart.js or Recharts.

## Research and Engineering Phases

## Phase 0: Foundation

Duration: 1 week

Tasks:

- finalize problem framing and terminology,
- confirm the threat model,
- create repo skeleton and contribution standards,
- define naming and documentation conventions.

Outputs:

- repository baseline,
- proposal draft,
- implementation plan.

## Phase 1: Threat Model and Feature Taxonomy

Duration: 2 weeks

Tasks:

- define attacker assumptions,
- separate exposure signals from password-choice signals,
- define allowed OSINT categories,
- define password-risk labels and online-guess budgets.

Outputs:

- `docs/THREAT_MODEL.md`,
- `docs/FEATURE_SCHEMA.md`,
- initial risk ontology.

## Phase 2: Synthetic Data Pipeline

Duration: 2 to 3 weeks

Tasks:

- generate synthetic employee rosters,
- generate realistic public-profile text,
- generate associated candidate-password datasets or mock password-creation tasks,
- build train/validation/test splits.

Outputs:

- synthetic persona generator,
- synthetic profile corpus,
- synthetic password-risk evaluation corpus.

## Phase 3: Exposure Engine Prototype

Duration: 2 weeks

Tasks:

- implement structured profile ingestion,
- implement NLP-based extraction,
- implement normalized attribute vectors,
- compute exposure score baselines.

Outputs:

- working ingestion and normalization pipeline,
- first exposure feature set,
- unit tests.

## Phase 4: Password Risk Engine Prototype

Duration: 3 weeks

Tasks:

- implement generic baseline meter,
- implement conditional feature engineering,
- train first targeted-risk classifier,
- calibrate outputs for online-risk classes.

Outputs:

- baseline model comparison,
- calibrated predictor,
- evaluation notebook.

## Phase 5: Policy Engine and Explanations

Duration: 2 weeks

Tasks:

- merge exposure and password scores,
- define policy mappings,
- generate human-readable explanations,
- test false-positive tradeoffs.

Outputs:

- policy engine,
- explanation renderer,
- threshold analysis report.

## Phase 6: Interfaces

Duration: 2 to 3 weeks

Tasks:

- implement CLI workflows,
- build initial FastAPI service,
- build dashboard prototype,
- add export support and audit logging.

Outputs:

- CLI usable for local experiments,
- API for batch scoring,
- dashboard MVP.

## Phase 7: Evaluation and Paper Readiness

Duration: 3 weeks

Tasks:

- benchmark against generic meters,
- run ablation studies,
- evaluate calibration and explanation quality,
- prepare tables, figures, and reproducibility artifacts.

Outputs:

- results package,
- paper-ready figures,
- experiment manifest.

## Backlog by Module

## Priority 1

- repo hygiene,
- feature schema,
- synthetic dataset generator,
- CLI scaffold,
- baseline risk model.

## Priority 2

- exposure scoring,
- conditional password-risk scoring,
- calibration,
- explanation engine.

## Priority 3

- dashboard,
- policy simulation tooling,
- user-study support materials.

## Suggested Initial Issues

1. `docs: write threat model and ethics boundaries`
2. `feat: define profile and attribute schemas`
3. `feat: add synthetic persona generator`
4. `feat: implement candidate password feature extraction`
5. `feat: add generic baseline meter wrapper`
6. `feat: build first exposure score baseline`
7. `feat: train first conditional risk classifier`
8. `feat: add CLI for batch scoring`
9. `feat: implement explanation templates`
10. `docs: define evaluation protocol`

## Data Strategy

### Preferred

- synthetic personas,
- organization-approved mock profiles,
- aggregate pattern statistics from public password corpora,
- consent-based test accounts if a later study is approved.

### Avoid

- profiling identifiable real individuals without authorization,
- using leaked credential pairs for re-identification,
- storing real production passwords.

## Evaluation Plan

### Model Metrics

- precision, recall, F1,
- AUROC,
- calibration error,
- false positive rate,
- decision-threshold stability.

### Explanation Metrics

- expert actionability rating,
- explanation fidelity,
- feature attribution stability.

### Operational Metrics

- latency,
- memory footprint,
- batch throughput,
- report generation time.

## Definition of Done for MVP

SignalLock MVP is complete when:

- a batch audit can ingest synthetic employee profiles,
- the system produces a valid exposure score,
- a local user can score a candidate password,
- the system outputs a calibrated risk class and explanation,
- a policy engine maps the result to one of a small set of security actions,
- baseline benchmark results are reproducible.

## Recommended Near-Term Build Order

1. Threat model and terminology.
2. Synthetic data generation.
3. Exposure ingestion and normalization.
4. Candidate-password scoring.
5. Score calibration.
6. Policy engine.
7. Explanations.
8. CLI.
9. Dashboard.
10. Evaluation package.
