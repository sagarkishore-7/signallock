"use client";

import { useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { api } from "@/lib/api";
import {
  ACTION_LABELS,
  type CompareBaselineResult,
  type HardeningRecommendation,
} from "@/lib/types";
import { RiskBadge } from "./RiskBadge";

export function PasswordTester({ subjectId }: { subjectId: string }) {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compare, setCompare] = useState<CompareBaselineResult | null>(null);
  const [rec, setRec] = useState<HardeningRecommendation | null>(null);

  async function run(event: FormEvent) {
    event.preventDefault();
    if (!password) return;
    setLoading(true);
    setError(null);
    try {
      const [c, r] = await Promise.all([
        api.compareBaseline(subjectId, password),
        api.recommend(subjectId, password),
      ]);
      setCompare(c);
      setRec(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setCompare(null);
      setRec(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={run} className="flex gap-2">
        <input
          type="text"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter a candidate password to test"
          className="flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent-700"
          autoComplete="off"
          spellCheck={false}
        />
        <button
          type="submit"
          disabled={loading || !password}
          className="rounded-lg bg-accent-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Testing…" : "Test"}
        </button>
      </form>

      <p className="text-xs text-ink-faint">
        The password is sent only to compute a score and is never stored or echoed
        back by the server.
      </p>

      {error && (
        <div className="rounded-lg border border-risk-high-ring bg-risk-high-bg p-3 text-sm text-risk-high-fg">
          {error}
        </div>
      )}

      {compare && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Cell label="Context-aware (SignalLock)">
            <RiskBadge band={compare.contextual_band} />
          </Cell>
          <Cell label="Context-free (zxcvbn)">
            <RiskBadge band={compare.baseline.band} />
          </Cell>
          <Cell label="Exposure premium">
            <span className="text-2xl font-semibold tracking-tight text-ink">
              {compare.premium.premium >= 0 ? "+" : ""}
              {compare.premium.premium.toFixed(2)}
            </span>
            <span className="ml-1 text-xs text-ink-faint">orders of magnitude</span>
          </Cell>
        </div>
      )}

      {compare && (
        <p className="text-xs leading-relaxed text-ink-subdued">
          The exposure premium is how many orders of magnitude of guessing effort
          this account&apos;s public OSINT removes. A large premium with a weak
          context-aware band but a strong context-free band means a password that
          looks fine to a generic meter is in fact predictable to a targeted
          attacker.
        </p>
      )}

      {rec && (
        <div className="surface p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">
            Recommended action
          </div>
          <div className="mt-1 text-lg font-semibold text-ink">
            {ACTION_LABELS[rec.primary_action]}
          </div>
          {rec.supporting_actions.length > 0 && (
            <div className="mt-1 text-sm text-ink-subdued">
              Supporting:{" "}
              {rec.supporting_actions.map((a) => ACTION_LABELS[a]).join(", ")}
            </div>
          )}
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-subdued">
            {rec.rationale.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Cell({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="surface p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">
        {label}
      </div>
      <div className="mt-2">{children}</div>
    </div>
  );
}
