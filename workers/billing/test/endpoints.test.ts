import { SELF, env } from 'cloudflare:test';
import { describe, it, expect, beforeEach } from 'vitest';
import { applyMigration } from './helpers';

declare const __MIGRATION_SQL__: string;

beforeEach(() => applyMigration(__MIGRATION_SQL__));

async function call(path: string, init: RequestInit & { userId?: string } = {}) {
  const headers = new Headers(init.headers);
  headers.set('content-type', 'application/json');
  if (init.userId) headers.set('x-user-id', init.userId);
  return SELF.fetch(`https://x${path}`, { ...init, headers });
}

describe('credit endpoints', () => {
  it('GET balance returns zero view for unknown user', async () => {
    const r = await call('/api/billing/credit/balance', { method: 'GET', userId: 'u-a' });
    expect(r.status).toBe(200);
    expect(await r.json()).toEqual({ balance: 0, held: 0 });
  });

  it('GET balance 400 on missing user header', async () => {
    const r = await call('/api/billing/credit/balance', { method: 'GET' });
    expect(r.status).toBe(400);
    expect(await r.json()).toMatchObject({ code: 'missing_user_id' });
  });

  it('POST hold 402 insufficient -> POST hold OK after grant', async () => {
    let r = await call('/api/billing/credit/hold', {
      method: 'POST',
      userId: 'u-b',
      body: JSON.stringify({ amount: 100 }),
    });
    expect(r.status).toBe(402);

    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-b', 500, 0, ?)",
    ).bind(Date.now()).run();

    r = await call('/api/billing/credit/hold', {
      method: 'POST',
      userId: 'u-b',
      body: JSON.stringify({ amount: 100 }),
    });
    expect(r.status).toBe(200);
    const body = await r.json<{ holdId: string; newBalance: number }>();
    expect(body.newBalance).toBe(400);
    expect(body.holdId).toMatch(/^h_/);
  });

  it('hold -> debit happy path', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-c', 1000, 0, ?)",
    ).bind(Date.now()).run();

    const h = await call('/api/billing/credit/hold', {
      method: 'POST', userId: 'u-c', body: JSON.stringify({ amount: 250 }),
    });
    const { holdId } = await h.json<{ holdId: string }>();

    const d = await call('/api/billing/credit/debit', {
      method: 'POST', userId: 'u-c', body: JSON.stringify({ holdId, actualAmount: 200 }),
    });
    expect(d.status).toBe(200);
    expect(await d.json()).toEqual({ newBalance: 800 });
  });

  it('debit returns 404 unknown hold', async () => {
    const r = await call('/api/billing/credit/debit', {
      method: 'POST', userId: 'u-d',
      body: JSON.stringify({ holdId: 'h-bogus', actualAmount: 5 }),
    });
    expect(r.status).toBe(404);
  });

  it('refund returns 200 idempotent on unknown hold', async () => {
    const r = await call('/api/billing/credit/refund', {
      method: 'POST', userId: 'u-e',
      body: JSON.stringify({ holdId: 'h-gone' }),
    });
    expect(r.status).toBe(200);
  });

  it('existing /api/billing/quota still works', async () => {
    const r = await call('/api/billing/quota', { method: 'GET' });
    expect(r.status).toBe(200);
    const body = await r.json<{ aiUsed: number; aiCap: number; tier: string }>();
    expect(body.aiCap).toBe(5);
  });
});
