"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { PublicProfile } from "@/lib/types";
import { Avatar } from "./Avatar";
import { PasswordTester } from "./PasswordTester";
import { SectionHeader } from "./SectionHeader";

export function PasswordTesterPage() {
  const [profiles, setProfiles] = useState<PublicProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const demo = await api.demoProfiles(20, 1);
        if (cancelled) return;
        setProfiles(demo.profiles);
        setSelectedId(demo.profiles[0]?.employee_id ?? "");
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return profiles;
    const q = search.toLowerCase();
    return profiles.filter(
      (p) =>
        p.full_name.toLowerCase().includes(q) ||
        p.title.toLowerCase().includes(q) ||
        p.department.toLowerCase().includes(q),
    );
  }, [profiles, search]);

  const selected = profiles.find((p) => p.employee_id === selectedId) ?? null;

  if (error) {
    return (
      <div className="surface bg-risk-critical-bg/40 p-5 text-sm text-risk-critical-fg">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Interactive mode"
        title="Password tester"
        description="Pick any synthetic profile and evaluate a candidate password against their public context. The tester compares heuristic and ML-assisted scoring side by side when the API was started with a trained model."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px,1fr]">
        <aside className="lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto">
          <div className="surface flex flex-col">
            <div className="border-b border-border p-4">
              <h3 className="text-sm font-semibold text-ink">
                Choose a profile
              </h3>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search profiles…"
                className="input mt-3 text-xs"
              />
            </div>
            <div className="divide-y divide-border">
              {loading ? (
                <div className="p-4 text-sm text-ink-muted">Loading…</div>
              ) : filtered.length === 0 ? (
                <div className="p-4 text-sm text-ink-muted">
                  No profiles match.
                </div>
              ) : (
                filtered.map((p) => (
                  <button
                    key={p.employee_id}
                    onClick={() => setSelectedId(p.employee_id)}
                    className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-muted/40 ${
                      selectedId === p.employee_id ? "bg-accent-50" : ""
                    }`}
                  >
                    <Avatar name={p.full_name} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm font-medium text-ink">
                        {p.full_name}
                      </div>
                      <div className="truncate text-xs text-ink-muted">
                        {p.title}
                      </div>
                    </div>
                    {selectedId === p.employee_id && (
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent-700" />
                    )}
                  </button>
                ))
              )}
            </div>
          </div>
        </aside>

        <section>
          {selected ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-muted/30 px-4 py-3 text-xs text-ink-subdued">
                <span className="font-medium text-ink">{selected.full_name}</span>
                <span className="mx-1.5 text-ink-faint">·</span>
                {selected.title}
                <span className="mx-1.5 text-ink-faint">·</span>
                {selected.organization}
                <span className="mx-1.5 text-ink-faint">·</span>
                {selected.location}
                <span className="mx-1.5 text-ink-faint">·</span>
                joined {selected.tenure_start_year}
              </div>
              <PasswordTester profile={selected} />
            </div>
          ) : (
            <div className="surface p-12 text-center text-sm text-ink-muted">
              Pick a profile to start.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
