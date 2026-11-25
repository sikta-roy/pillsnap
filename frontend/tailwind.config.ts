import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter Variable"', '"Noto Sans Devanagari"', "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#effcfa",
          100: "#d6f5f1",
          200: "#aeebe3",
          300: "#7bd9cf",
          400: "#45bfb4",
          500: "#24a39a",
          600: "#17837d",
          700: "#156965",
          800: "#155452",
          900: "#134645",
        },
        ink: { 900: "#0f2233", 700: "#334a5e", 500: "#5b7083", 300: "#a3b3c2" },
        sky: { 50: "#f2f8fe", 100: "#e3effc" },
      },
      borderRadius: { xl2: "1.25rem" },
      boxShadow: {
        card: "0 1px 2px rgba(15,34,51,.04), 0 8px 24px -12px rgba(15,34,51,.12)",
      },
      keyframes: {
        scan: { "0%": { top: "6%" }, "50%": { top: "88%" }, "100%": { top: "6%" } },
        fadeUp: { "0%": { opacity: "0", transform: "translateY(8px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
      },
      animation: { scan: "scan 2.2s ease-in-out infinite", fadeUp: "fadeUp .4s ease-out both" },
    },
  },
  plugins: [],
} satisfies Config;
