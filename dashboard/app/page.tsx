import { RosterClient } from "@/components/RosterClient";

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Organization roster</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Audit-mode exposure assessment for a synthetic employee roster. Click
          any row to drill into a per-user breakdown with explanation and
          interactive password testing.
        </p>
      </div>
      <RosterClient />
    </div>
  );
}
