import { RosterClient } from "@/components/RosterClient";

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Consented roster</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Audit-mode exposure assessment for the consented subjects (dummy
          personas and real participants). Click a row to drill into the exposure
          breakdown and test a candidate password.
        </p>
      </div>
      <RosterClient />
    </div>
  );
}
