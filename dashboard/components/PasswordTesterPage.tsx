"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { SubjectSummary } from "@/lib/types";
import { PasswordTester } from "./PasswordTester";
import { SectionHeader } from "./SectionHeader";

export function PasswordTesterPage() {
  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .subjects()
      .then((list) => {
        const withSnapshot = list.filter((s) => s.has_snapshot);
        setSubjects(withSnapshot);
        if (withSnapshot.length > 0) setSelected(withSnapshot[0].subject_id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Interactive mode"
        title="Password tester"
        description="Pick a consented subject and test how predictable a candidate password is against their public OSINT — context-aware vs a context-free meter, with the exposure premium."
      />

      {error && <div className="surface p-5 text-sm text-risk-high-fg">{error}</div>}

      <div className="surface p-5 space-y-4">
        <label className="block text-sm">
          <span className="text-xs font-medium uppercase tracking-wider text-ink-muted">
            Subject
          </span>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="mt-2 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent-700"
          >
            {subjects.map((s) => (
              <option key={s.subject_id} value={s.subject_id}>
                {s.subject_id}
                {s.is_dummy ? " (dummy)" : ""}
              </option>
            ))}
          </select>
        </label>

        {selected && <PasswordTester subjectId={selected} />}
      </div>
    </div>
  );
}
