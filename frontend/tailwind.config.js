/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:      '#0a0a0f',
        surface: '#141419',
        border:  '#1e1e2a',
        cyan:    '#00d4ff',
        amber:   '#ff9f43',
        green:   '#00c853',
        red:     '#ff4444',
        text:    '#e0e0e8',
        muted:   '#6b6b7e',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['DM Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
