/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "media", // follow system preference; no user toggle for v1
  theme: {
    extend: {
      fontFamily: {
        // Apple-like system font stack — falls through to native rendering
        // on every platform without shipping a webfont. Inter is the closest
        // open-source proxy for SF Pro if a user pins to Linux.
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "'SF Pro Text'",
          "'Inter'",
          "'Segoe UI'",
          "Roboto",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          "'SF Mono'",
          "'JetBrains Mono'",
          "ui-monospace",
          "Menlo",
          "monospace",
        ],
      },
      fontVariationSettings: {
        // Tabular figures keep number columns from jumping as values change.
        tabular: '"tnum"',
      },
      colors: {
        // Neutral palette tuned for the dashboard's "calm and sparse" feel.
        ink: {
          50: "#fafafa",
          100: "#f4f4f5",
          200: "#e4e4e7",
          300: "#d4d4d8",
          400: "#a1a1aa",
          500: "#71717a",
          600: "#52525b",
          700: "#3f3f46",
          800: "#27272a",
          900: "#18181b",
          950: "#09090b",
        },
        positive: "#10b981",
        negative: "#ef4444",
        warning: "#f59e0b",
      },
      animation: {
        "pulse-soft": "pulse-soft 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
    },
  },
  plugins: [],
};
