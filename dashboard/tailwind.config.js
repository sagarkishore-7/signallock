/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        // Surfaces and structure
        canvas: "#fafafa",
        surface: "#ffffff",
        muted: "#f5f5f7",
        border: {
          DEFAULT: "#e7e7eb",
          strong: "#d4d4d8",
        },
        // Foreground
        ink: {
          DEFAULT: "#0a0a0a",
          subdued: "#525866",
          muted: "#71717a",
          faint: "#a1a1aa",
        },
        // Brand accent (deep blue-green, professional security)
        accent: {
          DEFAULT: "#1e525f",
          50: "#f0f6f8",
          100: "#dceaee",
          200: "#bdd5dd",
          500: "#3d7d8c",
          600: "#2c6573",
          700: "#1e525f",
          900: "#0a3038",
        },
        // Risk severities — calibrated saturation, not alarming reds
        risk: {
          low: { fg: "#0d6938", bg: "#e6f4ea", ring: "#34a853" },
          medium: { fg: "#854d0e", bg: "#fef3c7", ring: "#d97706" },
          high: { fg: "#9a3412", bg: "#fee2d6", ring: "#ea580c" },
          critical: { fg: "#7f1d1d", bg: "#fee2e2", ring: "#b91c1c" },
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.04), 0 1px 1px rgba(0,0,0,0.02)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)",
        focus: "0 0 0 3px rgba(30, 82, 95, 0.15)",
      },
      borderRadius: {
        DEFAULT: "8px",
        lg: "12px",
        xl: "16px",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
    },
  },
  plugins: [],
};
