import { defineConfig, devices } from '@playwright/test';

// @ts-ignore — process is a Node.js global
const CI = !!process.env['CI'];

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: CI ? 1 : 0,
  use: {
    baseURL: 'http://localhost:4321',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  reporter: CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  webServer: [
    {
      command: 'cd ../api && uvicorn main:app --port 8000 --log-level info',
      url: 'http://localhost:8000/healthz',
      timeout: 60_000,
      reuseExistingServer: !CI,
      stdout: 'pipe',
      stderr: 'pipe',
      // @ts-ignore — process is a Node.js global
      env: { PYTHONUNBUFFERED: '1', PATH: process.env['PATH'] || '' },
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
