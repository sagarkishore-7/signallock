import type { RiskBand } from "@/lib/types";

const STYLES: Record<
  RiskBand,
  { bg: string; fg: string; ring: string; label: string }
> = {
  LOW: {
    bg: "bg-risk-low-bg",
    fg: "text-risk-low-fg",
    ring: "bg-risk-low-ring",
    label: "Low",
  },
  MEDIUM: {
    bg: "bg-risk-medium-bg",
    fg: "text-risk-medium-fg",
    ring: "bg-risk-medium-ring",
    label: "Medium",
  },
  HIGH: {
    bg: "bg-risk-high-bg",
    fg: "text-risk-high-fg",
    ring: "bg-risk-high-ring",
    label: "High",
  },
  CRITICAL: {
    bg: "bg-risk-critical-bg",
    fg: "text-risk-critical-fg",
    ring: "bg-risk-critical-ring",
    label: "Critical",
  },
};

export function RiskBadge({
  band,
  size = "md",
}: {
  band: RiskBand;
  size?: "sm" | "md";
}) {
  const s = STYLES[band];
  const sizing =
    size === "sm"
      ? "px-1.5 py-0.5 text-[10px] gap-1"
      : "px-2.5 py-0.5 text-xs gap-1.5";
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${s.bg} ${s.fg} ${sizing}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${s.ring}`} />
      {s.label}
    </span>
  );
}
