"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ExposureAssessment, PublicProfile, RiskBand } from "@/lib/types";
import { Avatar } from "./Avatar";
import { RiskBadge } from "./RiskBadge";

interface Row {
  profile: PublicProfile;
  assessment: ExposureAssessment;
}

const BAND_ORDER: Record<RiskBand, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

type SortKey = "band" | "score" | "name" | "department";
type SortDir = "asc" | "desc";

export function ExposureHeatmap({
  profiles,
  assessments,
}: {
  profiles: PublicProfile[];
  assessments: ExposureAssessment[];
}) {
  const [filter, setFilter] = useState<RiskBand | "ALL">("ALL");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({
    key: "band",
    dir: "asc",
  });

  const rows: Row[] = useMemo(() => {
    const byId = new Map(assessments.map((a) => [a.employee_id, a]));
    return profiles
      .map((profile) => ({ profile, assessment: byId.get(profile.employee_id)! }))
      .filter((row) => row.assessment !== undefined);
  }, [profiles, assessments]);

  const filtered = useMemo(() => {
    let out = rows;
    if (filter !== "ALL") {
      out = out.filter((r) => r.assessment.band === filter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      out = out.filter(
        (r) =>
          r.profile.full_name.toLowerCase().includes(q) ||
          r.profile.title.toLowerCase().includes(q) ||
          r.profile.department.toLowerCase().includes(q),
      );
    }
    out = [...out].sort((a, b) => {
      let cmp = 0;
      switch (sort.key) {
        case "band":
          cmp = BAND_ORDER[a.assessment.band] - BAND_ORDER[b.assessment.band];
          break;
        case "score":
          cmp = b.assessment.score - a.assessment.score;
          break;
        case "name":
          cmp = a.profile.full_name.localeCompare(b.profile.full_name);
          break;
        case "department":
          cmp = a.profile.department.localeCompare(b.profile.department);
          break;
      }
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return out;
  }, [rows, filter, search, sort]);

  const counts = useMemo(() => {
    const c: Record<RiskBand, number> = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    for (const r of rows) c[r.assessment.band]++;
    return c;
  }, [rows]);

  function toggleSort(key: SortKey) {
    setSort((s) =>
      s.key === key
        ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "score" ? "desc" : "asc" },
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <SearchInput value={search} onChange={setSearch} />

        <div className="flex flex-wrap items-center gap-1 text-xs">
          {(["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((b) => (
            <FilterChip
              key={b}
              label={b}
              active={filter === b}
              count={b === "ALL" ? rows.length : counts[b as RiskBand]}
              onClick={() => setFilter(b)}
            />
          ))}
        </div>

        <div className="ml-auto text-xs text-ink-muted">
          Showing <span className="font-mono text-ink">{filtered.length}</span> of{" "}
          <span className="font-mono text-ink">{rows.length}</span>
        </div>
      </div>

      <div className="surface overflow-hidden">
        <table className="min-w-full border-collapse text-sm">
          <thead className="border-b border-border bg-muted/40">
            <tr className="text-left text-xs font-medium uppercase tracking-wider text-ink-muted">
              <SortableHeader
                label="Employee"
                sortKey="name"
                current={sort}
                onClick={toggleSort}
                className="px-5 py-3"
              />
              <SortableHeader
                label="Title · Dept"
                sortKey="department"
                current={sort}
                onClick={toggleSort}
                className="px-5 py-3"
              />
              <SortableHeader
                label="Score"
                sortKey="score"
                current={sort}
                onClick={toggleSort}
                className="px-5 py-3 text-right"
              />
              <SortableHeader
                label="Band"
                sortKey="band"
                current={sort}
                onClick={toggleSort}
                className="px-5 py-3"
              />
              <th className="px-5 py-3">Top driver</th>
              <th className="w-12 px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-5 py-12 text-center text-sm text-ink-muted"
                >
                  No employees match the current filters.
                </td>
              </tr>
            ) : (
              filtered.map(({ profile, assessment }) => (
                <RosterRow
                  key={profile.employee_id}
                  profile={profile}
                  assessment={assessment}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RosterRow({
  profile,
  assessment,
}: {
  profile: PublicProfile;
  assessment: ExposureAssessment;
}) {
  return (
    <tr className="group border-b border-border last:border-b-0 transition-colors duration-100 hover:bg-muted/40">
      <td className="px-5 py-3.5">
        <Link
          href={`/users/${profile.employee_id}`}
          className="flex items-center gap-3"
        >
          <Avatar name={profile.full_name} size="sm" />
          <div>
            <div className="font-medium text-ink group-hover:text-accent-700">
              {profile.full_name}
            </div>
            <div className="font-mono text-[11px] text-ink-faint">
              {profile.employee_id}
            </div>
          </div>
        </Link>
      </td>
      <td className="px-5 py-3.5 text-ink-subdued">
        <div>{profile.title}</div>
        <div className="text-xs text-ink-faint">{profile.department}</div>
      </td>
      <td className="px-5 py-3.5 text-right">
        <span className="font-mono text-sm text-ink">
          {assessment.score.toFixed(1)}
        </span>
        <span className="ml-1 text-xs text-ink-faint">/100</span>
      </td>
      <td className="px-5 py-3.5">
        <RiskBadge band={assessment.band} />
      </td>
      <td className="max-w-xs px-5 py-3.5">
        <span className="line-clamp-1 text-ink-subdued" title={assessment.top_factors[0]}>
          {assessment.top_factors[0] ?? "—"}
        </span>
      </td>
      <td className="px-5 py-3.5 text-right">
        <Link
          href={`/users/${profile.employee_id}`}
          className="inline-flex items-center justify-center rounded-md p-1 text-ink-faint transition-all duration-150 hover:bg-surface hover:text-ink group-hover:text-ink-subdued"
          aria-label={`Drill into ${profile.full_name}`}
        >
          <ChevronRightIcon />
        </Link>
      </td>
    </tr>
  );
}

function FilterChip({
  label,
  active,
  count,
  onClick,
}: {
  label: string;
  active: boolean;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-all duration-150 ${
        active
          ? "border border-ink bg-ink text-white"
          : "border border-transparent text-ink-subdued hover:border-border-strong hover:bg-muted hover:text-ink"
      }`}
    >
      <span>{label}</span>
      <span
        className={`rounded font-mono ${
          active ? "text-white/70" : "text-ink-faint"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

function SortableHeader({
  label,
  sortKey,
  current,
  onClick,
  className = "",
}: {
  label: string;
  sortKey: SortKey;
  current: { key: SortKey; dir: SortDir };
  onClick: (k: SortKey) => void;
  className?: string;
}) {
  const isActive = current.key === sortKey;
  return (
    <th className={className}>
      <button
        onClick={() => onClick(sortKey)}
        className={`group/sort inline-flex items-center gap-1 ${
          isActive ? "text-ink" : "hover:text-ink"
        }`}
      >
        {label}
        <span
          className={`text-[8px] transition-opacity ${
            isActive ? "opacity-100" : "opacity-0 group-hover/sort:opacity-50"
          }`}
        >
          {current.dir === "asc" ? "▲" : "▼"}
        </span>
      </button>
    </th>
  );
}

function SearchInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint">
        <SearchIcon />
      </span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search by name, title, department…"
        className="input w-72 pl-8"
      />
    </div>
  );
}

function ChevronRightIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
    >
      <path d="M6 4l4 4-4 4" />
    </svg>
  );
}

function SearchIcon() {
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
      <circle cx="7" cy="7" r="5" />
      <path d="M11 11l3 3" />
    </svg>
  );
}
