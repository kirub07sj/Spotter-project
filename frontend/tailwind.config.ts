import type { Config } from 'tailwindcss';

// Design tokens (docs/04 §4). Components use these names, never raw hex values.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        risk: {
          low: '#2E9E5B',
          moderate: '#E3B505',
          high: '#F08A24',
          severe: '#D7263D',
          notravel: '#5B1A8B',
          unknown: '#9AA0A6',
        },
        route: { a: '#2563EB', b: '#0891B2', c: '#64748B' },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config;
