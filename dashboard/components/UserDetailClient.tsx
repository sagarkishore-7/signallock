"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api";
import { AXIS_LABELS, type ExposureAssessment } from "@/lib/types";
import { MetricCard } from "./MetricCard";
import { PasswordTester } from "./PasswordTester";
import { RiskBadge } from "./RiskBadge";
import { SectionHeader } from "./SectionHeader";

export function UserDetailClient({ subjectId }: { subjectId: string }) {
  const [exposure, setExposure] = useState<ExposureAssessment | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .scoreExposure(subjectId)
      .then(setExposure)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [subjectId]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionHeader eyebrow="Subject" title={subjectId} />
        <Link href="/" className="text-sm text-accent-700 hover:underline">
          ← Roster
        </Link>
      </div>

      {error && (
        <div className="surface p-5 text-sm text-risk-high-fg">{error}</div>
      )}

      {!exposure && !error && (
        <div className="surface p-5 text-sm text-ink-muted">Loading exposure…</div>
      )}

      {exposure && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <MetricCard
              label="Exposure score"
              value={exposure.score.toFixed(1)}
              emphasis
              hint={<RiskBadge band={exposure.band} size="sm" />}
            />
            <MetricCard
              label="Linkability multiplier"
              value={`×${exposure.linkability_multiplier.toFixed(2)}`}
              hint={`linkability ${exposure.linkability_score.toFixed(0)}/100`}
            />
            <MetricCard
              label="Base surface"
              value={exposure.base_surface.toFixed(1)}
              hint="before linkability amplification"
            />
          </div>

          <div className="surface p-5">
            <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">
              Exposure axes
            </div>
            <div className="mt-4 space-y-3">
              {Object.entries(exposure.axis_scores).map(([axis, value]) => (
                <div key={axis}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-ink-subdued">
                      {AXIS_LABELS[axis] ?? axis}
                    </span>
                    <span className="tabular-nums text-ink-muted">
                      {value.toFixed(0)}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-line">
                    <div
                      className="h-1.5 rounded-full bg-accent-700"
                      style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            {exposure.top_factors.length > 0 && (
              <div className="mt-5 text-sm text-ink-subdued">
                <span className="text-ink-muted">Top factors: </span>
                {exposure.top_factors.join(" · ")}
              </div>
            )}
          </div>

          <div className="surface p-5">
            <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">
              Test a candidate password against this subject
            </div>
            <div className="mt-4">
              <PasswordTester subjectId={subjectId} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
