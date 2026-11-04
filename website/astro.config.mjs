import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  site: 'https://grzes71.github.io',
  base: process.env.ASTRO_BASE_URL ?? '/jabberwocky',
  trailingSlash: 'ignore',
  integrations: [tailwind()],
  output: 'static',
});

