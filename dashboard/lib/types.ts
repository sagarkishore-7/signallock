// TypeScript types mirroring the SignalLock v2 API (src/signallock/api.py).
// Keep in sync with the Python dataclasses if the backend changes.

export type RiskBand = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

// Accessibility tier to score against (public-only / +connection-gated / all).
export type Visibility = "public" | "gated" | "all";

export type HardeningAction =
  | "ALLOW"
  | "WARN"
  | "REQUIRE_STRONGER_PASSWORD"
  | "ENFORCE_MFA"
  | "STEP_UP_AUTHENTICATION"
  | "PRIORITIZE_AWARENESS_TRAINING";

// GET /subjects
export interface SubjectSummary {
  subject_id: string;
  is_dummy: boolean;
  has_snapshot: boolean;
  exposure_score?: number;
  exposure_band?: RiskBand;
}

// POST /score/exposure
export interface ExposureAssessment {
  subject_id: string;
  score: number;
  band: RiskBand;
  base_surface: number;
  linkability_multiplier: number;
  axis_scores: Record<string, number>;
  linkability_score: number;
  top_factors: string[];
}

// POST /score/predictability
export interface PredictabilityAssessment {
  subject_id: string;
  band: RiskBand;
  reached_budget: number | null;
  guesses_to_crack: number | null;
  matched_category: string | null;
  budget_ceiling: number;
}

export interface BaselineStrength {
  zxcvbn_score: number;
  guesses_log10: number;
  band: RiskBand;
}

export interface ExposurePremium {
  baseline_log10: number;
  contextual_log10: number;
  premium: number;
}

// POST /compare-baseline
export interface CompareBaselineResult {
  subject_id: string;
  contextual_band: RiskBand;
  baseline: BaselineStrength;
  premium: ExposurePremium;
}

// POST /recommend
export interface HardeningRecommendation {
  subject_id: string;
  exposure_score: number;
  exposure_band: RiskBand;
  predictability_band: RiskBand;
  combined_score: number;
  primary_action: HardeningAction;
  supporting_actions: HardeningAction[];
  rationale: string[];
}

export interface Health {
  status: string;
  version: string;
  subjects: number;
}

// Human-readable axis labels for the exposure breakdown.
export const AXIS_LABELS: Record<string, string> = {
  discoverability: "Discoverability",
  professional_visibility: "Professional visibility",
  personal_trivia_richness: "Personal-trivia richness",
  breach_exposure: "Breach exposure",
  temporal_footprint: "Temporal footprint",
};

export const ACTION_LABELS: Record<HardeningAction, string> = {
  ALLOW: "Allow",
  WARN: "Warn",
  REQUIRE_STRONGER_PASSWORD: "Require stronger password",
  ENFORCE_MFA: "Enforce MFA",
  STEP_UP_AUTHENTICATION: "Step-up authentication",
  PRIORITIZE_AWARENESS_TRAINING: "Prioritize awareness training",
};
