import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

test('AI assist personality field, accept, writes override', async ({ page }) => {
  const cai = readFileSync(join(__dirname, '..', '..', 'public', 'samples', 'cai.txt'), 'utf-8');
  await page.goto('/chara-convert/convert');
  await page.getByPlaceholder(/paste your character/i).fill(cai);
  await page.getByRole('button', { name: /detect source/i }).click();
  await expect(page.getByText(/% ready/)).toBeVisible({ timeout: 10_000 });

  const card = page.locator('[data-field="personality"]');
  await card.hover();
  await card.getByRole('button', { name: 'AI' }).click();
  const panel = page.getByRole('dialog', { name: /AI assist for personality/i });
  await expect(panel).toBeVisible();
  await panel.getByRole('button', { name: /generate/i }).click();
  await expect(panel).toContainText(/Aerin is calm/, { timeout: 10_000 });
  await panel.getByRole('button', { name: /accept/i }).click();
  await expect(card).toContainText(/calm and observant/);
});
