import type { Config } from 'tailwindcss';
import { tokens } from './design/tailwind.theme';

export default {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: { extend: tokens },
} satisfies Config;
