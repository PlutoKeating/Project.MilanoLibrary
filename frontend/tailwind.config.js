/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./pages/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        'retro-bg': '#0a0a0f',
        'retro-bg-secondary': '#111118',
        'retro-border': '#1e1e2e',
        'retro-cyan': '#00f0ff',
        'retro-fuchsia': '#ff00a0',
      },
    },
  },
  plugins: [],
}
