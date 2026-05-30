import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://studio.aichathub.uk',
  base: '/chara-convert/',
  integrations: [react(), tailwind({ applyBaseStyles: false })],
  output: 'static',
  outDir: './dist/chara-convert',
  build: { inlineStylesheets: 'auto' },
});
