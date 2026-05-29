import { describe, it, expect, beforeEach } from 'vitest';
import { Miniflare } from 'miniflare';

// Worker script using the format Miniflare expects
const workerScript = `
const FREE_CAP = 5;
const TTL_S = 60 * 60 * 26;

function dayKey(ip) {
  const d = new Date().toISOString().slice(0, 10);
  return \`quota:ai:\${ip}:\${d}\`;
}

async function readQuota(kv, ip) {
  const used = parseInt((await kv.get(dayKey(ip))) ?? '0', 10);
  return { aiUsed: used, aiCap: FREE_CAP, tier: 'free' };
}

async function bumpQuota(kv, ip) {
  const k = dayKey(ip);
  const used = parseInt((await kv.get(k)) ?? '0', 10) + 1;
  await kv.put(k, String(used), { expirationTtl: TTL_S });
  return used;
}

const TODO = (todo) => new Response(JSON.stringify({ todo }), {
  status: 501, headers: { 'content-type': 'application/json' },
});

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ip = request.headers.get('cf-connecting-ip') ?? '0.0.0.0';

    if (url.pathname === '/api/billing/quota' && request.method === 'GET') {
      const body = await readQuota(env.RATE_LIMIT_KV, ip);
      return Response.json(body);
    }
    if (url.pathname === '/api/billing/bump' && request.method === 'POST') {
      const used = await bumpQuota(env.RATE_LIMIT_KV, ip);
      return Response.json({ aiUsed: used });
    }
    if (url.pathname === '/api/billing/checkout') return TODO('Creem cutover 2026-10');
    if (url.pathname === '/api/billing/webhook') return TODO('Creem cutover 2026-10');
    return new Response('not found', { status: 404 });
  },
};
`;

let mf: Miniflare;

beforeEach(async () => {
  mf = new Miniflare({
    script: workerScript,
    kvNamespaces: ['RATE_LIMIT_KV'],
  });
});

describe('billing worker', () => {
  it('GET /api/billing/quota returns free defaults', async () => {
    const res = await mf.dispatchFetch('http://x/api/billing/quota');
    const json = await res.json() as any;
    expect(json.tier).toBe('free');
    expect(json.aiCap).toBe(5);
    expect(json.aiUsed).toBe(0);
  });

  it('POST /api/billing/bump increments per IP', async () => {
    await mf.dispatchFetch('http://x/api/billing/bump', { method: 'POST' });
    const res = await mf.dispatchFetch('http://x/api/billing/bump', { method: 'POST' });
    expect((await res.json() as any).aiUsed).toBe(2);
  });

  it('POST /api/billing/checkout returns 501', async () => {
    const res = await mf.dispatchFetch('http://x/api/billing/checkout', { method: 'POST' });
    expect(res.status).toBe(501);
  });
});
