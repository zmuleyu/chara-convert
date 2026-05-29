import { describe, it, expect, beforeEach } from 'vitest';
import { env, SELF } from 'cloudflare:test';

beforeEach(async () => {
  const keys = await env.RATE_LIMIT_KV.list();
  await Promise.all(keys.keys.map((k: { name: string }) => env.RATE_LIMIT_KV.delete(k.name)));
});

describe('billing worker', () => {
  it('GET /api/billing/quota returns free defaults', async () => {
    const res = await SELF.fetch('http://x/api/billing/quota');
    const json = await res.json() as any;
    expect(json.tier).toBe('free');
    expect(json.aiCap).toBe(5);
    expect(json.aiUsed).toBe(0);
  });

  it('POST /api/billing/bump increments per IP', async () => {
    await SELF.fetch('http://x/api/billing/bump', { method: 'POST' });
    const res = await SELF.fetch('http://x/api/billing/bump', { method: 'POST' });
    expect((await res.json() as any).aiUsed).toBe(2);
  });

  it('POST /api/billing/checkout returns 501', async () => {
    const res = await SELF.fetch('http://x/api/billing/checkout', { method: 'POST' });
    expect(res.status).toBe(501);
  });
});
