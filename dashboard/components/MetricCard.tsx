import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  hint,
  emphasis = false,
  trend,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  emphasis?: boolean;
  trend?: "up" | "down" | "flat";
}) {
  const valueClass = emphasis
    ? "text-3xl font-semibold tracking-tight text-ink"
    : "text-2xl font-semibold tracking-tight text-ink";
  return (
    <div className="surface surface-hover p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-ink-muted">
          {label}
        </span>
        {trend && <TrendDot direction={trend} />}
      </div>
      <div className={`mt-2 ${valueClass}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-faint">{hint}</div>}
    </div>
  );
}

function TrendDot({ direction }: { direction: "up" | "down" | "flat" }) {
  const colors = {
    up: "bg-risk-low-ring",
    down: "bg-risk-medium-ring",
    flat: "bg-ink-faint",
  };
  return <span className={`h-1.5 w-1.5 rounded-full ${colors[direction]}`} />;
}
