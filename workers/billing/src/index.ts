import { readQuota, bumpQuota } from './quota';

interface Env { RATE_LIMIT_KV: KVNamespace }

const TODO = (todo: string) => new Response(JSON.stringify({ todo }), {
  status: 501, headers: { 'content-type': 'application/json' },
});

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const ip = req.headers.get('cf-connecting-ip') ?? '0.0.0.0';

    if (url.pathname === '/api/billing/quota' && req.method === 'GET') {
      const body = await readQuota(env.RATE_LIMIT_KV, ip);
      return Response.json(body);
    }
    if (url.pathname === '/api/billing/bump' && req.method === 'POST') {
      const used = await bumpQuota(env.RATE_LIMIT_KV, ip);
      return Response.json({ aiUsed: used });
    }
    if (url.pathname === '/api/billing/checkout') return TODO('Creem cutover 2026-10');
    if (url.pathname === '/api/billing/webhook') return TODO('Creem cutover 2026-10');
    return new Response('not found', { status: 404 });
  },
};
