/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Nordic dark palette — matches YggdrasilStudio
        rune: {
          50: '#f0f0f5',
          100: '#d1d1de',
          200: '#a3a3bd',
          300: '#75759c',
          400: '#47477b',
          500: '#2a2a5a',
          600: '#23234d',
          700: '#1c1c40',
          800: '#151533',
          900: '#0e0e26',
          950: '#08081a',
        },
        ember: {
          DEFAULT: '#e8553d',
          light: '#f07a66',
          dark: '#c4392a',
        },
        fjord: {
          DEFAULT: '#3b82f6',
          light: '#60a5fa',
          dark: '#2563eb',
        },
        gold: {
          DEFAULT: '#f59e0b',
          light: '#fbbf24',
          dark: '#d97706',
        },
        yggdrasil: {
          green: '#22c55e',
          bark: '#78350f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
