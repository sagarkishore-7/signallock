// Hash-derived colored circle with initials. Deterministic per name.

const PALETTE = [
  { bg: "#e8f1f5", fg: "#1e525f" }, // accent
  { bg: "#fef3c7", fg: "#92400e" }, // amber
  { bg: "#ddd6fe", fg: "#5b21b6" }, // violet
  { bg: "#dbeafe", fg: "#1e40af" }, // blue
  { bg: "#dcfce7", fg: "#166534" }, // green
  { bg: "#fce7f3", fg: "#9d174d" }, // pink
  { bg: "#cffafe", fg: "#155e75" }, // cyan
];

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Avatar({
  name,
  size = "md",
}: {
  name: string;
  size?: "sm" | "md" | "lg" | "xl";
}) {
  const palette = PALETTE[hashString(name) % PALETTE.length];
  const dim = {
    sm: "h-8 w-8 text-xs",
    md: "h-10 w-10 text-sm",
    lg: "h-12 w-12 text-base",
    xl: "h-16 w-16 text-xl",
  }[size];
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold tracking-wide ${dim}`}
      style={{ backgroundColor: palette.bg, color: palette.fg }}
    >
      {initials(name)}
    </span>
  );
}
