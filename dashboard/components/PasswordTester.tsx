"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type {
  HardeningExplanation,
  ModelScoringComparison,
  PublicProfile,
} from "@/lib/types";
import type { RecommendResponse } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";

const POLICY_PROFILES = ["balanced", "strict", "usability"] as const;

export function PasswordTester({ profile }: { profile: PublicProfile }) {
  const [password, setPassword] = useState("");
  const [policy, setPolicy] = useState<(typeof POLICY_PROFILES)[number]>("balanced");
  const [recResult, setRecResult] = useState<RecommendResponse | null>(null);
  const [explanation, setExplanation] = useState<HardeningExplanation | null>(null);
  const [comparison, setComparison] = useState<ModelScoringComparison | null>(null);
  const [hasModel, setHasModel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usedMl, setUsedMl] = useState(false);

  async function evaluate(useMl: boolean) {
    if (!password) return;
    setBusy(true);
    setError(null);
    setComparison(null);
    setUsedMl(useMl);
    try {
      const health = await api.health();
      setHasModel(health.model_loaded);

      const effectiveMl = useMl && health.model_loaded;
      const [rec, exp] = await Promise.all([
        api.recommend(profile, password, policy, effectiveMl),
        api.explain(profile, password, policy, effectiveMl),
      ]);
      setRecResult(rec);
      setExplanation(exp);
      if (health.model_loaded) {
        const cmp = await api.compareScoring(profile, password, policy);
        setComparison(cmp);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface overflow-hidden">
      <div className="border-b border-border bg-gradient-to-br from-accent-50 to-surface px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-accent-700">
              Interactive mode
            </div>
            <h3 className="mt-1 text-lg font-semibold text-ink">
              Test a candidate password
            </h3>
            <p className="mt-1 text-sm text-ink-subdued">
              Score a hypothetical password against this user&apos;s public profile context.
              The password is never echoed in responses; only matched profile
              tokens appear in the explanation.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-5 p-6">
        <div className="space-y-3">
          <label className="block">
            <div className="mb-1.5 text-xs font-medium uppercase tracking-wider text-ink-muted">
              Candidate password
            </div>
            <input
              type="text"
              autoComplete="off"
              spellCheck={false}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="e.g. Priya2014!"
              className="input font-mono text-sm"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !busy && password) {
                  evaluate(false);
                }
              }}
            />
          </label>

          <div className="flex flex-wrap items-end gap-3">
            <div>
              <div className="mb-1.5 text-xs font-medium uppercase tracking-wider text-ink-muted">
                Policy profile
              </div>
              <SegmentedControl value={policy} options={POLICY_PROFILES} onChange={setPolicy} />
            </div>
            <div className="ml-auto flex gap-2">
              <button
                onClick={() => evaluate(false)}
                disabled={busy || !password}
                className="btn-secondary"
              >
                {busy && !usedMl ? <Spinner /> : <BoltIcon />}
                Heuristic
              </button>
              <button
                onClick={() => evaluate(true)}
                disabled={busy || !password}
                className="btn-primary"
              >
                {busy && usedMl ? <Spinner /> : <SparkIcon />}
                ML-assisted
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-md border border-risk-critical-ring/30 bg-risk-critical-bg/40 p-3 text-xs text-risk-critical-fg">
            {error}
          </div>
        )}

        {recResult && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <ResultStat
              label="Password band"
              value={<RiskBadge band={recResult.recommendation.password_band} />}
              hint={`heuristic score ${recResult.password_assessment.score.toFixed(1)} / 100`}
            />
            <ResultStat
              label="Combined score"
              value={
                <span className="font-mono text-2xl font-semibold text-ink">
                  {recResult.recommendation.combined_score.toFixed(1)}
                </span>
              }
              hint={`policy: ${recResult.recommendation.policy_profile}`}
            />
            <ResultStat
              label="Primary action"
              value={
                <span className="font-mono text-sm font-semibold text-ink">
                  {recResult.recommendation.primary_action}
                </span>
              }
              hint={
                recResult.recommendation.ml_assisted
                  ? "ml-assisted band"
                  : "heuristic band"
              }
            />
          </div>
        )}

        {comparison && (
          <ComparisonPanel comparison={comparison} />
        )}

        {explanation && (
          <div className="rounded-lg border border-border bg-gradient-to-b from-surface to-muted/30 p-5">
            <div className="mb-2 flex items-center gap-2">
              <span className="rounded bg-accent-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-accent-700">
                Explanation
              </span>
              <span className="text-xs text-ink-faint">
                template-based · derived from matched tokens
              </span>
            </div>
            <p className="text-sm leading-relaxed text-ink">
              {explanation.full_explanation}
            </p>
            {explanation.password_explanation.factor_sentences.length > 0 && (
              <div className="mt-3 border-t border-border pt-3">
                <div className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-muted">
                  Risk factors
                </div>
                <ul className="space-y-1.5">
                  {explanation.password_explanation.factor_sentences.map((s, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-xs text-ink-subdued"
                    >
                      <span className="mt-0.5 inline-block h-1 w-1 shrink-0 rounded-full bg-ink-faint" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {!hasModel && recResult && (
          <p className="text-xs text-ink-faint">
            <strong>Tip:</strong> start the server with{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono">
              --model-file &lt;pkl&gt;
            </code>{" "}
            to enable ML-assisted scoring and the side-by-side comparison panel.
          </p>
        )}
      </div>
    </div>
  );
}

function ComparisonPanel({ comparison }: { comparison: ModelScoringComparison }) {
  const bandsAgree = comparison.bands_agree;
  const actionsAgree = comparison.actions_agree;
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-5">
      <div className="mb-3 flex items-center gap-2">
        <span className="rounded bg-accent-700 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white">
          Heuristic vs ML
        </span>
        <span className="text-xs text-ink-faint">side-by-side comparison</span>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
            Heuristic
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <RiskBadge band={comparison.heuristic_password_band} />
            <ArrowRightIcon />
            <span className="font-mono text-xs text-ink">
              {comparison.heuristic_action}
            </span>
          </div>
        </div>
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
            ML
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <RiskBadge band={comparison.ml_predicted_band} />
            <ArrowRightIcon />
            <span className="font-mono text-xs text-ink">
              {comparison.ml_action}
            </span>
          </div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-3 text-xs">
        <Agreement label="bands" agree={bandsAgree} />
        <Agreement label="actions" agree={actionsAgree} />
      </div>
    </div>
  );
}

function Agreement({ label, agree }: { label: string; agree: boolean }) {
  const cls = agree
    ? "border-risk-low-ring/30 bg-risk-low-bg text-risk-low-fg"
    : "border-risk-medium-ring/30 bg-risk-medium-bg text-risk-medium-fg";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 ${cls}`}
    >
      {agree ? <CheckIcon /> : <DotIcon />}
      <span className="font-medium">
        {label} {agree ? "agree" : "disagree"}
      </span>
    </span>
  );
}

function ResultStat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-surface p-4">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
        {label}
      </div>
      <div className="mt-1.5">{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-faint">{hint}</div>}
    </div>
  );
}

function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: readonly T[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-border-strong bg-surface p-0.5">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`rounded px-3 py-1 text-xs font-medium capitalize transition-all duration-150 ${
            value === opt
              ? "bg-ink text-white"
              : "text-ink-subdued hover:text-ink"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

function Spinner() {
  return (
    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
  );
}

function BoltIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-3.5 w-3.5"
      aria-hidden
    >
      <path d="M9 1L3 9h4l-1 6 6-8H8l1-6z" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-3.5 w-3.5"
      aria-hidden
    >
      <path d="M8 1l1.5 4.5L14 7l-4.5 1.5L8 13l-1.5-4.5L2 7l4.5-1.5L8 1z" />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      className="h-3 w-3 text-ink-faint"
    >
      <path d="M3 8h10M9 4l4 4-4 4" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3 w-3"
    >
      <path d="M3 8l3 3 7-7" />
    </svg>
  );
}

function DotIcon() {
  return <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />;
}
