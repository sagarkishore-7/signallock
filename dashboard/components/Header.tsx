"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function Header() {
  const pathname = usePathname();
  const [status, setStatus] = useState<{ ok: boolean; subjects: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((h) => {
        if (!cancelled) setStatus({ ok: h.status === "ok", subjects: h.subjects });
      })
      .catch(() => {
        if (!cancelled) setStatus({ ok: false, subjects: 0 });
      });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3.5">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-semibold tracking-tight text-ink">Eidolon</span>
          <span className="hidden rounded border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-ink-faint sm:inline">
            audit
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          <NavLink href="/" active={pathname === "/"}>
            Roster
          </NavLink>
          <NavLink href="/test" active={pathname?.startsWith("/test") ?? false}>
            Password Tester
          </NavLink>
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <StatusIndicator status={status} />
          <a
            href="https://github.com/sagarkishore-7/signallock"
            target="_blank"
            rel="noreferrer"
            className="btn-ghost text-xs"
          >
            <GithubIcon />
            <span className="hidden sm:inline">GitHub</span>
          </a>
        </div>
      </div>
    </header>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`relative rounded-md px-3 py-1.5 text-sm transition-colors duration-150 ${
        active
          ? "text-ink bg-muted"
          : "text-ink-subdued hover:text-ink hover:bg-muted/60"
      }`}
    >
      {children}
    </Link>
  );
}

function StatusIndicator({
  status,
}: {
  status: { ok: boolean; subjects: number } | null;
}) {
  if (status === null) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-ink-faint">
        <span className="h-1.5 w-1.5 rounded-full bg-ink-faint animate-pulse" />
        Connecting…
      </div>
    );
  }
  if (!status.ok) {
    return (
      <div className="flex items-center gap-1.5 rounded-full border border-risk-critical-ring/40 bg-risk-critical-bg px-2.5 py-0.5 text-xs font-medium text-risk-critical-fg">
        <span className="h-1.5 w-1.5 rounded-full bg-risk-critical-ring" />
        API offline
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-risk-low-ring/40 bg-risk-low-bg px-2.5 py-0.5 text-xs font-medium text-risk-low-fg">
      <span className="h-1.5 w-1.5 rounded-full bg-risk-low-ring" />
      <span>API connected</span>
      <span className="text-ink-muted">·</span>
      <span className="font-mono text-[10px]">
        {status.subjects} subjects
      </span>
    </div>
  );
}

function Logo() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="h-6 w-6"
    >
      <path
        d="M12 2L4 6v6c0 5 3.5 9 8 10 4.5-1 8-5 8-10V6l-8-4z"
        stroke="#1e525f"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M9 12.5l2 2 4-4.5"
        stroke="#1e525f"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.16c-3.2.7-3.88-1.36-3.88-1.36-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.69.08-.69 1.15.08 1.75 1.18 1.75 1.18 1.02 1.74 2.67 1.24 3.32.95.1-.74.4-1.24.72-1.53-2.55-.29-5.24-1.27-5.24-5.66 0-1.25.45-2.27 1.18-3.07-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.17a10.96 10.96 0 015.74 0c2.19-1.48 3.15-1.17 3.15-1.17.62 1.58.23 2.75.11 3.04.73.8 1.18 1.82 1.18 3.07 0 4.4-2.69 5.36-5.25 5.65.41.36.78 1.06.78 2.14v3.18c0 .31.2.67.79.55C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5z" />
    </svg>
  );
}
