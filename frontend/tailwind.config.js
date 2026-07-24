/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0a0a0f",
          elevated: "#13131a",
          surface: "#1c1c26",
          hover: "#252533",
        },
        accent: {
          DEFAULT: "#10b981",
          hover: "#059669",
          subtle: "rgba(16, 185, 129, 0.12)",
        },
        text: {
          DEFAULT: "#e5e7eb",
          muted: "#9ca3af",
          subtle: "#6b7280",
        },
        border: {
          DEFAULT: "#2a2a38",
          subtle: "#1f1f29",
        },
        warning: "#f59e0b",
        danger: "#ef4444",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "10px",
      },
      keyframes: {
        pop: {
          "0%":   { opacity: "0", transform: "scale(0.85) translateY(12px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
      },
      animation: {
        pop: "pop 0.25s ease-out",
      },
    },
  },
  plugins: [],
};
