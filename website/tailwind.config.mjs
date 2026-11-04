/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        fantasy: {
          bg: '#070a08',
          surface: '#0d130f',
          surfaceLight: '#141d18',
          border: '#1c2c22',
          borderLight: '#284032',
          gold: '#d4af37',
          goldDim: '#997c22',
          flame: '#ff7700',
          flameDim: '#c45500',
          phosphor: '#00e676',
          phosphorDim: '#009944',
          vorpal: '#b366ff',
          vorpalDim: '#7922cc',
          text: '#e8efe9',
          muted: '#8da092',
          dark: '#030604',
        },
      },
      fontFamily: {
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          '"Liberation Mono"',
          '"Courier New"',
          'monospace',
        ],
        serif: [
          '"Cinzel"',
          'Georgia',
          'Cambria',
          '"Times New Roman"',
          'Times',
          'serif',
        ],
      },
      boxShadow: {
        'fantasy-gold': '0 0 20px rgba(212, 175, 55, 0.25)',
        'fantasy-flame': '0 0 20px rgba(255, 119, 0, 0.3)',
        'fantasy-green': '0 0 20px rgba(0, 230, 118, 0.25)',
        'fantasy-vorpal': '0 0 20px rgba(179, 102, 255, 0.25)',
      },
    },
  },
  plugins: [],
};

