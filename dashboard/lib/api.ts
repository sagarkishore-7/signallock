// Thin client for the SignalLock v2 FastAPI service.
// Configure the base URL via NEXT_PUBLIC_API_BASE (default http://localhost:8000).
// Start the backend with CORS for the dashboard dev server:
//   python -m signallock serve --cors-origins http://localhost:3000

import type {
  CompareBaselineResult,
  ExposureAssessment,
  HardeningRecommendation,
  Health,
  PredictabilityAssessment,
  SubjectSummary,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${path} failed: ${response.status} ${text}`);
  }
  return response.json();
}

function post<T>(path: string, body: unknown): Promise<T> {
  return jsonFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export const api = {
  apiBase: API_BASE,

  health: () => jsonFetch<Health>("/healthz"),

  subjects: () => jsonFetch<SubjectSummary[]>("/subjects"),

  scoreExposure: (subjectId: string) =>
    post<ExposureAssessment>("/score/exposure", { subject_id: subjectId }),

  scorePredictability: (subjectId: string, password: string) =>
    post<PredictabilityAssessment>("/score/predictability", {
      subject_id: subjectId,
      password,
    }),

  compareBaseline: (subjectId: string, password: string) =>
    post<CompareBaselineResult>("/compare-baseline", {
      subject_id: subjectId,
      password,
    }),

  recommend: (subjectId: string, password: string) =>
    post<HardeningRecommendation>("/recommend", {
      subject_id: subjectId,
      password,
    }),
};
