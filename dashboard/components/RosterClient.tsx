"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api";
import type { SubjectSummary } from "@/lib/types";
import { RiskBadge } from "./RiskBadge";

export function RosterClient() {
  const [subjects, setSubjects] = useState<SubjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .subjects()
      .then(setSubjects)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (error) {
    return (
      <div className="surface p-5 text-sm text-ink-subdued">
        <p className="font-medium text-risk-high-fg">Could not reach the API.</p>
        <p className="mt-1">{error}</p>
        <p className="mt-3 text-xs text-ink-faint">
          Start the backend with CORS:{" "}
          <code>
            python -m eidolon serve --cors-origins http://localhost:3000
          </code>
        </p>
      </div>
    );
  }

  if (!subjects) {
    return <div className="surface p-5 text-sm text-ink-muted">Loading roster…</div>;
  }

  return (
    <div className="surface overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs uppercase tracking-wider text-ink-muted">
            <th className="px-5 py-3 font-medium">Subject</th>
            <th className="px-5 py-3 font-medium">Type</th>
            <th className="px-5 py-3 font-medium">Exposure</th>
            <th className="px-5 py-3 font-medium">Band</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody>
          {subjects.map((s) => (
            <tr
              key={s.subject_id}
              className="border-b border-line/60 last:border-0 hover:bg-surface-hover"
            >
              <td className="px-5 py-3 font-medium text-ink">{s.subject_id}</td>
              <td className="px-5 py-3 text-ink-subdued">
                {s.is_dummy ? "dummy" : "consented"}
              </td>
              <td className="px-5 py-3 text-ink-subdued">
                {s.exposure_score != null ? s.exposure_score.toFixed(1) : "—"}
              </td>
              <td className="px-5 py-3">
                {s.exposure_band ? <RiskBadge band={s.exposure_band} size="sm" /> : "—"}
              </td>
              <td className="px-5 py-3 text-right">
                {s.has_snapshot ? (
                  <Link
                    href={`/users/${encodeURIComponent(s.subject_id)}`}
                    className="text-xs font-medium text-accent-700 hover:underline"
                  >
                    Drill in →
                  </Link>
                ) : (
                  <span className="text-xs text-ink-faint">no snapshot</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
