"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { ExposureAssessment, PublicProfile } from "@/lib/types";
import { ExposureHeatmap } from "./ExposureHeatmap";
import { MetricCard } from "./MetricCard";
import { SectionHeader } from "./SectionHeader";

export function RosterClient() {
  const [count, setCount] = useState(20);
  const [seed, setSeed] = useState(1);
  const [profiles, setProfiles] = useState<PublicProfile[]>([]);
  const [assessments, setAssessments] = useState<ExposureAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modelLoaded, setModelLoaded] = useState(false);

  async function load(c: number, s: number) {
    setLoading(true);
    setError(null);
    try {
      const [demo, health] = await Promise.all([
        api.demoProfiles(c, s),
        api.health(),
      ]);
      const exposure = await api.scoreExposureBatch(demo.profiles);
      setProfiles(demo.profiles);
      setAssessments(exposure.assessments);
      setModelLoaded(health.model_loaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(count, seed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stats = useMemo(() => {
    const total = assessments.length;
    if (total === 0)
      return {
        total: 0,
        atRisk: 0,
        avgScore: 0,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
      };
    let critical = 0,
      high = 0,
      medium = 0,
      low = 0,
      sum = 0;
    for (const a of assessments) {
      sum += a.score;
      if (a.band === "CRITICAL") critical++;
      else if (a.band === "HIGH") high++;
      else if (a.band === "MEDIUM") medium++;
      else low++;
    }
    return {
      total,
      atRisk: critical + high,
      avgScore: sum / total,
      critical,
      high,
      medium,
      low,
    };
  }, [assessments]);

  return (
    <div className="space-y-10">
      <SectionHeader
        eyebrow="Audit mode"
        title="Organization roster"
        description="Per-employee exposure assessment derived from organization-approved public profile data. Click any row to drill into a per-user breakdown with explanation and interactive password testing."
        action={
          <div className="flex items-center gap-2">
            <ConfigInput
              label="Roster"
              value={count}
              min={1}
              max={200}
              onChange={setCount}
            />
            <ConfigInput label="Seed" value={seed} onChange={setSeed} />
            <button
              onClick={() => load(count, seed)}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? <Spinner /> : <RefreshIcon />}
              <span>Reload</span>
            </button>
          </div>
        }
      />

      {error && <ErrorPanel message={error} />}

      {!error && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCard
            label="Roster size"
            value={stats.total}
            hint="synthetic profiles"
          />
          <MetricCard
            label="At risk"
            value={
              <span className="text-risk-high-fg">{stats.atRisk}</span>
            }
            hint={`${stats.critical} critical · ${stats.high} high`}
          />
          <MetricCard
            label="Avg exposure"
            value={
              <span className="font-mono">
                {stats.avgScore.toFixed(1)}
                <span className="text-base text-ink-faint"> /100</span>
              </span>
            }
            hint="weighted across roster"
          />
          <MetricCard
            label="Scoring engine"
            value={
              <span className="text-base font-medium">
                {modelLoaded ? "Heuristic + ML" : "Heuristic only"}
              </span>
            }
            hint={modelLoaded ? "trained classifier loaded" : "no model attached"}
          />
        </div>
      )}

      {!loading && !error && profiles.length > 0 && (
        <ExposureHeatmap profiles={profiles} assessments={assessments} />
      )}

      {loading && !error && (
        <div className="surface flex h-64 items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-ink-muted">
            <Spinner size="lg" />
            <span className="text-sm">Loading roster…</span>
          </div>
        </div>
      )}
    </div>
  );
}

function ConfigInput({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 rounded-md border border-border-strong bg-surface px-2 py-1 text-xs">
      <span className="text-ink-muted">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-12 bg-transparent text-right font-mono text-sm text-ink focus:outline-none"
      />
    </label>
  );
}

function ErrorPanel({ message }: { message: string }) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  return (
    <div className="surface border-risk-critical-ring/30 bg-risk-critical-bg/40 p-5">
      <div className="flex items-start gap-3">
        <WarningIcon />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-risk-critical-fg">
            Could not reach the SignalLock API
          </h3>
          <p className="mt-1 text-sm text-ink-subdued">
            Make sure the FastAPI server is running on{" "}
            <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-xs">
              {apiBase}
            </code>{" "}
            with CORS enabled for this dashboard&apos;s origin.
          </p>
          <pre className="mt-3 overflow-x-auto rounded border border-border bg-surface p-3 font-mono text-xs text-ink-subdued">
            python -m signallock serve --port 8000 \{"\n"}
            {"  "}--cors-origins http://localhost:3000
          </pre>
          <p className="mt-3 text-xs text-ink-faint">{message}</p>
        </div>
      </div>
    </div>
  );
}

function Spinner({ size = "sm" }: { size?: "sm" | "lg" }) {
  const dim = size === "lg" ? "h-6 w-6" : "h-3.5 w-3.5";
  return (
    <span
      className={`${dim} animate-spin rounded-full border-2 border-current border-t-transparent`}
      aria-label="loading"
    />
  );
}

function RefreshIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3.5 w-3.5"
    >
      <path d="M14 8a6 6 0 11-1.76-4.24" />
      <path d="M14 2.5V6h-3.5" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="h-5 w-5 text-risk-critical-fg"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.008v.008H12v-.008z"
      />
    </svg>
  );
}
