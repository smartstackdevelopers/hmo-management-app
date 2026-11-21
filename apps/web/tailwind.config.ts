import type { Config } from "tailwindcss";

// Blue & White design system (docs/audit/HMORE_UI_UX_DESIGN_SPEC_COMPLETE_BLUE.pdf §3).
// `teal-*`, `forest-*` and `cream` are kept as brand aliases so existing pages pick up the
// blue palette without renaming classes in every file. New code should prefer `brand-*` / `navy-*`.
const brand = {
  50: "#eff6ff",
  100: "#dbeafe",
  200: "#bfdbfe",
  300: "#93c5fd",
  400: "#60a5fa",
  500: "#3b82f6",
  600: "#2563eb",
  700: "#1d4ed8",
  800: "#1e40af",
  900: "#1e3a8a",
  950: "#172554",
};

const navy = {
  700: "#1e3a8a",
  800: "#1e2f6b",
  900: "#172554",
};

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand,
        navy,
        teal: brand,
        forest: navy,
        cream: "#f3f7fd",
        ink: "#0b1220",
      },
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans"',
          "Inter",
          "Segoe UI",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06)",
        lift: "0 8px 24px rgba(29, 78, 216, 0.12)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
      },
    },
  },
  plugins: [],
};

export default config;
