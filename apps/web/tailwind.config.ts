import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        forest: {
          900: "#0f3b32",
          800: "#164a3f",
          700: "#1c5c4e",
        },
        cream: "#f6f3ee",
      },
    },
  },
  plugins: [],
};

export default config;
