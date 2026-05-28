import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const SAMPLES = join(process.cwd(), 'public', 'samples');

for (const sample of ['cai.txt', 'chai.txt']) {
  test(`${sample} → fictionlab happy path`, async ({ page }) => {
    const text = readFileSync(join(SAMPLES, sample), 'utf-8');
    await page.goto('/chara-convert/convert');
    await page.getByPlaceholder(/paste your character/i).fill(text);
    await page.getByRole('button', { name: /detect source/i }).click();
    await expect(page.getByText(/Detected:/)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/% ready/)).toBeVisible({ timeout: 15_000 });
    const nameCard = page.locator('[data-field="name"]');
    await expect(nameCard).toBeVisible();
    await page.getByRole('button', { name: /copy all/i }).click();
  });
}

test('sillytavern.json upload happy path', async ({ page }) => {
  await page.goto('/chara-convert/convert');
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(join(SAMPLES, 'sillytavern.json'));
  await expect(page.getByText(/Detected:/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/% ready/)).toBeVisible({ timeout: 15_000 });
});
