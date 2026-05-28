import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    exclude: ['node_modules', 'dist', '.astro', 'tests/e2e/**'],
  },
  resolve: { alias: { '~': '/src' } },
});
