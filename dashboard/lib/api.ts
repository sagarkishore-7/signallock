// Thin client for the SignalLock FastAPI service.
// Configure the base URL via NEXT_PUBLIC_API_BASE.

import type {
  ExposureAssessment,
  HardeningExplanation,
  HardeningRecommendation,
  ModelScoringComparison,
  PasswordRiskAssessment,
  PublicProfile,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${path} failed: ${response.status} ${text}`);
  }
  return response.json();
}

export interface DemoProfilesResponse {
  count: number;
  organization: string;
  seed: number;
  profiles: PublicProfile[];
}

export interface ExposureBatchResponse {
  count: number;
  assessments: ExposureAssessment[];
}

export interface RecommendResponse {
  exposure: ExposureAssessment;
  password_assessment: PasswordRiskAssessment;
  recommendation: HardeningRecommendation;
}

export const api = {
  health: () => jsonFetch<{ status: string; version: string; model_loaded: boolean }>("/healthz"),

  policies: () => jsonFetch<unknown[]>("/policies"),

  demoProfiles: (count = 10, seed = 1, organization = "ExampleCorp") =>
    jsonFetch<DemoProfilesResponse>(
      `/demo/profiles?count=${count}&seed=${seed}&organization=${encodeURIComponent(organization)}`,
    ),

  scoreExposureBatch: (profiles: PublicProfile[]) =>
    jsonFetch<ExposureBatchResponse>("/score/exposure", {
      method: "POST",
      body: JSON.stringify({ profiles }),
    }),

  recommend: (
    profile: PublicProfile,
    password: string,
    policyProfile = "balanced",
    ml = false,
  ) =>
    jsonFetch<RecommendResponse>(`/recommend?ml=${ml}`, {
      method: "POST",
      body: JSON.stringify({
        profile,
        password,
        policy_profile: policyProfile,
      }),
    }),

  explain: (
    profile: PublicProfile,
    password: string,
    policyProfile = "balanced",
    ml = false,
  ) =>
    jsonFetch<HardeningExplanation>(`/explain?ml=${ml}`, {
      method: "POST",
      body: JSON.stringify({
        profile,
        password,
        policy_profile: policyProfile,
      }),
    }),

  compareScoring: (
    profile: PublicProfile,
    password: string,
    policyProfile = "balanced",
  ) =>
    jsonFetch<ModelScoringComparison>("/compare-scoring", {
      method: "POST",
      body: JSON.stringify({
        profile,
        password,
        policy_profile: policyProfile,
      }),
    }),
};
