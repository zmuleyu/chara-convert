import { defineConfig } from 'vitest/config';
import { readFileSync } from 'fs';
import { execSync } from 'child_process';
import path from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
  },
});
