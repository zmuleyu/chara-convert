import { test, expect } from '@playwright/test';

test('landing renders CTA', async ({ page }) => {
  await page.goto('/chara-convert/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Move your character');
});

test('convert page mounts stepper sections', async ({ page }) => {
  await page.goto('/chara-convert/convert');
  for (const id of ['step-source', 'step-gap', 'step-convert', 'step-edit', 'step-export']) {
    await expect(page.locator(`#${id}`)).toBeVisible();
  }
});
