/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "var(--color-bg-base)",
        raised: "var(--color-bg-raised)",
        overlay: "var(--color-bg-overlay)",
        inset: "var(--color-bg-inset)",
        ink: "var(--color-text)",
        muted: "var(--color-text-muted)",
        accent: "var(--color-accent)",
        line: "var(--color-border)",
        "line-subtle": "var(--color-border-subtle)",
        "line-strong": "var(--color-border-strong)",
        supported: "var(--color-status-supported)",
        contradicted: "var(--color-status-contradicted)",
        uncertain: "var(--color-status-uncertain)",
        evidence: "var(--color-span-evidence)",
        temporal: "var(--color-span-temporal)",
        boilerplate: "var(--color-span-boilerplate)",
      },
      fontFamily: {
        sans: "var(--font-sans)",
        mono: "var(--font-mono)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
      },
      boxShadow: {},
    },
  },
  plugins: [],
};
