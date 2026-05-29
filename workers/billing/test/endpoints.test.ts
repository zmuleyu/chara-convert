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

  // A.1.x-M1: error envelope code field must distinguish caller-error (4xx)
  // from transient/server-error (5xx) so credit_client.py can apply different
  // retry policy. See workers/billing/src/types.ts for code-→-semantics map.
  it('unknown credit subpath inside DO returns 404 not_found (not bad_request)', async () => {
    const r = await call('/api/billing/credit/bogus', { method: 'POST', userId: 'u-z', body: '{}' });
    expect(r.status).toBe(404);
    expect(await r.json()).toMatchObject({ code: 'not_found' });
  });

  it('malformed JSON body returns 400 bad_request', async () => {
    const r = await call('/api/billing/credit/hold', { method: 'POST', userId: 'u-z', body: 'not-json' });
    expect(r.status).toBe(400);
    expect(await r.json()).toMatchObject({ code: 'bad_request' });
  });

  it('hold with non-numeric amount returns 400 bad_request', async () => {
    const r = await call('/api/billing/credit/hold', {
      method: 'POST', userId: 'u-z', body: JSON.stringify({ amount: 'cheap' }),
    });
    expect(r.status).toBe(400);
    expect(await r.json()).toMatchObject({ code: 'bad_request' });
  });

  // Phase C: CORS — apps/web (4321) calls credit/* from the browser, so the
  // Worker must echo Access-Control-Allow-Origin for the allow-listed origins
  // and short-circuit OPTIONS preflight.
  it('OPTIONS preflight returns 204 with CORS headers when Origin is allow-listed', async () => {
    const r = await SELF.fetch('https://x/api/billing/credit/balance', {
      method: 'OPTIONS',
      headers: { origin: 'http://localhost:4321' },
    });
    expect(r.status).toBe(204);
    expect(r.headers.get('access-control-allow-origin')).toBe('http://localhost:4321');
    expect(r.headers.get('access-control-allow-methods')).toContain('GET');
    expect(r.headers.get('access-control-allow-headers')).toContain('x-user-id');
  });

  it('GET balance echoes CORS Allow-Origin for allow-listed origin', async () => {
    const r = await SELF.fetch('https://x/api/billing/credit/balance', {
      method: 'GET',
      headers: { 'x-user-id': 'u-cors', origin: 'http://127.0.0.1:4321' },
    });
    expect(r.status).toBe(200);
    expect(r.headers.get('access-control-allow-origin')).toBe('http://127.0.0.1:4321');
  });

  it('omits CORS headers when Origin is not allow-listed', async () => {
    const r = await SELF.fetch('https://x/api/billing/credit/balance', {
      method: 'GET',
      headers: { 'x-user-id': 'u-cors', origin: 'https://attacker.example' },
    });
    expect(r.status).toBe(200);
    expect(r.headers.get('access-control-allow-origin')).toBeNull();
  });
});
