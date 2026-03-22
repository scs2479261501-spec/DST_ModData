/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        dst: {
          darkest: '#1a1410',
          dark: '#2a2218',
          brown: '#3d3226',
          'brown-alt': '#352b20',
          border: '#5c4a3a',
          gold: '#e8b84b',
          rust: '#c75b39',
          green: '#7db862',
          blue: '#5b9bd5',
          purple: '#9b7ec8',
          deadwood: '#8a7060',
          text: '#e8dcc8',
          'text-dim': '#a89880',
          'text-title': '#f0e0c0',
          'text-muted': '#6b5d4d',
        },
      },
      fontFamily: {
        title: ['Cinzel', 'serif'],
        body: ['Crimson Text', 'Noto Serif SC', 'serif'],
        hans: ['Noto Serif SC', 'serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(92,74,58,0.3), 0 12px 40px rgba(0,0,0,0.4)',
        'card-inset': 'inset 0 0 20px rgba(0,0,0,0.3)',
        'card-inset-sm': 'inset 0 0 15px rgba(0,0,0,0.2)',
        'gold-glow': '0 0 8px rgba(232, 184, 75, 0.2)',
        navbar: '0 2px 8px rgba(0,0,0,0.5)',
      },
      borderRadius: {
        dst: '4px',
      },
    },
  },
  plugins: [],
};
