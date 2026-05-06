// TypeScript types mirroring the Python schemas in src/signallock/schemas.py.
// Keep these in sync if backend dataclasses change.

export type RiskBand = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type HardeningAction =
  | "ALLOW"
  | "WARN"
  | "REQUIRE_STRONGER_PASSWORD"
  | "ENFORCE_MFA"
  | "STEP_UP_AUTHENTICATION"
  | "PRIORITIZE_AWARENESS_TRAINING";

export type RoleSeniority =
  | "INDIVIDUAL_CONTRIBUTOR"
  | "MANAGER"
  | "DIRECTOR"
  | "VP"
  | "C_SUITE";

export interface PublicProfile {
  employee_id: string;
  full_name: string;
  title: string;
  department: string;
  organization: string;
  role_seniority: RoleSeniority;
  email_format: string;
  location: string;
  tenure_start_year: number;
  platforms: string[];
  public_usernames: string[];
  interests: string[];
  preferred_name?: string | null;
  education?: string | null;
  bio?: string | null;
}

export interface ExposureAssessment {
  employee_id: string;
  score: number;
  band: RiskBand;
  component_scores: Record<string, number>;
  top_factors: string[];
}

export interface PasswordRiskAssessment {
  employee_id: string;
  password_length: number;
  score: number;
  band: RiskBand;
  generic_signals: Record<string, number>;
  contextual_signals: Record<string, number>;
  matched_tokens: Record<string, string[]>;
  top_factors: string[];
}

export interface HardeningRecommendation {
  employee_id: string;
  exposure_score: number;
  exposure_band: RiskBand;
  password_score: number;
  password_band: RiskBand;
  combined_score: number;
  policy_profile: string;
  primary_action: HardeningAction;
  supporting_actions: HardeningAction[];
  rationale: string[];
  ml_assisted: boolean;
}

export interface ExposureExplanation {
  employee_id: string;
  exposure_score: number;
  exposure_band: RiskBand;
  summary: string;
  factor_sentences: string[];
}

export interface PasswordRiskExplanation {
  employee_id: string;
  password_score: number;
  password_band: RiskBand;
  summary: string;
  factor_sentences: string[];
}

export interface HardeningExplanation {
  employee_id: string;
  primary_action: HardeningAction;
  action_sentence: string;
  exposure_explanation: ExposureExplanation;
  password_explanation: PasswordRiskExplanation;
  full_explanation: string;
}

export interface ModelScoringComparison {
  employee_id: string;
  password_length: number;
  exposure_score: number;
  exposure_band: RiskBand;
  heuristic_password_band: RiskBand;
  ml_predicted_band: RiskBand;
  bands_agree: boolean;
  heuristic_action: HardeningAction;
  ml_action: HardeningAction;
  actions_agree: boolean;
  heuristic_combined_score: number;
  ml_combined_score: number;
  heuristic_recommendation: HardeningRecommendation;
  ml_recommendation: HardeningRecommendation;
}
