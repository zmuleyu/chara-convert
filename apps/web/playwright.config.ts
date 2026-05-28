import { defineConfig, devices } from '@playwright/test';

// @ts-ignore — process is a Node.js global
const CI = !!process.env['CI'];

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  use: { baseURL: 'http://localhost:4321' },
  webServer: [
    {
      command: 'cd ../api && uvicorn main:app --port 8000',
      url: 'http://localhost:8000/healthz',
      timeout: 60_000,
      reuseExistingServer: !CI,
    },
    {
      command: 'npm run preview -- --port 4321',
      url: 'http://localhost:4321/chara-convert/',
      timeout: 60_000,
      reuseExistingServer: !CI,
      env: { PUBLIC_API_BASE: 'http://localhost:8000' },
    },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
