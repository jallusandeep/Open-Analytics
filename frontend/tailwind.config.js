/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "IBM Plex Mono", "Consolas", "monospace"]
      },
      colors: {
        oa: {
          dark: "#050505",
          panel: "#0B0B0D",
          card: "#111113",
          border: "#252529",
          text: "#F5F5F6",
          muted: "#A1A1AA",
          accent: "#7C3AED"
        }
      }
    }
  },
  plugins: []
}