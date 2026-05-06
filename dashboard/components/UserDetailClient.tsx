"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ExposureAssessment, PublicProfile } from "@/lib/types";
import { Avatar } from "./Avatar";
import { PasswordTester } from "./PasswordTester";
import { RiskBadge } from "./RiskBadge";

export function UserDetailClient({
  employeeId,
  rosterCount,
  rosterSeed,
}: {
  employeeId: string;
  rosterCount: number;
  rosterSeed: number;
}) {
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [exposure, setExposure] = useState<ExposureAssessment | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const demo = await api.demoProfiles(rosterCount, rosterSeed);
        const target = demo.profiles.find((p) => p.employee_id === employeeId);
        if (!target) {
          if (!cancelled) setError(`Employee ${employeeId} not found in roster`);
          return;
        }
        const exposureBatch = await api.scoreExposureBatch([target]);
        if (cancelled) return;
        setProfile(target);
        setExposure(exposureBatch.assessments[0]);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [employeeId, rosterCount, rosterSeed]);

  const sortedComponents = useMemo(() => {
    if (!exposure) return [];
    return Object.entries(exposure.component_scores).sort((a, b) => b[1] - a[1]);
  }, [exposure]);

  const maxComponent = sortedComponents[0]?.[1] ?? 1;

  if (error) {
    return (
      <div className="surface bg-risk-critical-bg/40 p-5 text-sm text-risk-critical-fg">
        {error}
      </div>
    );
  }

  if (!profile || !exposure) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-ink-faint border-t-transparent" />
      </div>
    );
  }

  const seniority = profile.role_seniority.replace(/_/g, " ").toLowerCase();

  return (
    <div className="space-y-8">
      <nav className="flex items-center gap-1.5 text-sm text-ink-muted">
        <Link href="/" className="hover:text-ink">
          Roster
        </Link>
        <span className="text-ink-faint">/</span>
        <span className="font-mono text-xs text-ink">{profile.employee_id}</span>
      </nav>

      <div className="surface p-6 sm:p-8">
        <div className="flex flex-wrap items-start gap-6">
          <Avatar name={profile.full_name} size="xl" />
          <div className="flex-1">
            <h1 className="text-2xl font-semibold tracking-tight text-ink">
              {profile.full_name}
            </h1>
            <p className="mt-1 text-sm text-ink-subdued">
              {profile.title} · {profile.department}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
              <Pill>{seniority}</Pill>
              <Pill>{profile.organization}</Pill>
              <Pill>{profile.location}</Pill>
              <Pill>joined {profile.tenure_start_year}</Pill>
            </div>
          </div>
          <div className="flex items-center gap-6 border-l border-border pl-6">
            <div>
              <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">
                Exposure score
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-mono text-4xl font-semibold tracking-tight text-ink">
                  {exposure.score.toFixed(1)}
                </span>
                <span className="text-sm text-ink-faint">/ 100</span>
              </div>
              <div className="mt-2">
                <RiskBadge band={exposure.band} />
              </div>
            </div>
          </div>
        </div>

        <ScoreBar score={exposure.score} band={exposure.band} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="surface p-6">
          <SectionTitle
            title="Top exposure drivers"
            hint="ranked by contribution to score"
          />
          {exposure.top_factors.length === 0 ? (
            <p className="mt-4 text-sm text-ink-muted">
              No significant exposure factors identified.
            </p>
          ) : (
            <ol className="mt-4 space-y-2">
              {exposure.top_factors.map((f, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 rounded-md border border-border bg-muted/30 p-3"
                >
                  <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-100 font-mono text-[10px] font-semibold text-accent-700">
                    {i + 1}
                  </span>
                  <span className="text-sm text-ink">{f}</span>
                </li>
              ))}
            </ol>
          )}
        </div>

        <div className="surface p-6">
          <SectionTitle
            title="Component breakdown"
            hint={`${sortedComponents.length} signals contributing`}
          />
          <ul className="mt-4 space-y-2.5">
            {sortedComponents.map(([key, value]) => (
              <li key={key}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="text-ink-subdued">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono text-ink">{value.toFixed(2)}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-accent-700 transition-all duration-500 ease-smooth"
                    style={{
                      width: `${maxComponent === 0 ? 0 : (value / maxComponent) * 100}%`,
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="surface p-6">
        <SectionTitle
          title="Public profile snapshot"
          hint="organization-approved attributes used for scoring"
        />
        <dl className="mt-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
          <DetailRow label="Location" value={profile.location} />
          <DetailRow
            label="Public usernames"
            value={profile.public_usernames.join(", ") || "—"}
          />
          <DetailRow
            label="Email format"
            value={
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                {profile.email_format}
              </code>
            }
          />
          <DetailRow
            label="Platforms"
            value={
              <div className="flex flex-wrap gap-1">
                {profile.platforms.map((p) => (
                  <code
                    key={p}
                    className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-ink-subdued"
                  >
                    {p}
                  </code>
                ))}
              </div>
            }
          />
          <DetailRow
            label="Interests"
            value={profile.interests.join(", ") || "—"}
          />
          {profile.education && (
            <DetailRow label="Education" value={profile.education} />
          )}
          {profile.bio && (
            <div className="md:col-span-2">
              <DetailRow
                label="Public bio"
                value={
                  <span className="text-xs leading-relaxed text-ink-subdued">
                    {profile.bio}
                  </span>
                }
              />
            </div>
          )}
        </dl>
      </div>

      <PasswordTester profile={profile} />
    </div>
  );
}

function ScoreBar({ score, band }: { score: number; band: string }) {
  const percent = Math.max(0, Math.min(100, score));
  const colorByBand: Record<string, string> = {
    LOW: "bg-risk-low-ring",
    MEDIUM: "bg-risk-medium-ring",
    HIGH: "bg-risk-high-ring",
    CRITICAL: "bg-risk-critical-ring",
  };
  return (
    <div className="mt-6">
      <div className="relative h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-smooth ${colorByBand[band]}`}
          style={{ width: `${percent}%` }}
        />
        {/* threshold ticks */}
        <div className="absolute inset-y-0 left-[30%] w-px bg-border-strong/60" />
        <div className="absolute inset-y-0 left-[55%] w-px bg-border-strong/60" />
        <div className="absolute inset-y-0 left-[75%] w-px bg-border-strong/60" />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px] text-ink-faint">
        <span>0</span>
        <span>30</span>
        <span>55</span>
        <span>75</span>
        <span>100</span>
      </div>
    </div>
  );
}

function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {hint && <span className="text-xs text-ink-faint">{hint}</span>}
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-border-strong bg-muted px-2.5 py-0.5 text-xs text-ink-subdued">
      {children}
    </span>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs font-medium uppercase tracking-wider text-ink-muted">
        {label}
      </dt>
      <dd className="text-ink">{value}</dd>
    </div>
  );
}
