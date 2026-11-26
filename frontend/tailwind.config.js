/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        border: "var(--border)",
        card: "var(--card)",
        primary: {
          DEFAULT: "var(--primary)",
          hover: "var(--primary-hover)",
        },
        risk: {
          verylow: "#10b981", // emerald
          low: "#34d399",     // green-medium
          moderate: "#eab308", // amber
          high: "#f97316",    // orange
          veryhigh: "#ef4444" // red
        }
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
}
