import { readQuota, bumpQuota } from './quota';
import type { Env, CreditError } from './types';

export { CreditDO } from './credit-do';

const TODO = (todo: string) => new Response(JSON.stringify({ todo }), {
  status: 501, headers: { 'content-type': 'application/json' },
});

function err(status: number, code: CreditError['code'], message: string): Response {
  const body: CreditError = { code, message };
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  });
}

function requireUserId(req: Request): string | Response {
  const u = req.headers.get('x-user-id');
  if (!u) return err(400, 'missing_user_id', 'X-User-Id header is required');
  return u;
}

// Forward a public credit request to the per-user DurableObject. The DO does
// all body validation and runs the credit logic under input-gate serialization
// — Worker is a thin proxy. See docs/specs/2026-05-30-credit-router-phase-A1-races.md.
async function proxyToCreditDO(url: URL, req: Request, env: Env, userId: string): Promise<Response> {
  const stub = env.CREDIT_DO.get(env.CREDIT_DO.idFromName(userId));
  const internalReq = new Request(`https://credit-do${url.pathname}`, req);
  try {
    return await stub.fetch(internalReq);
  } catch (e) {
    console.error('CreditDO unreachable:', e);
    return err(503, 'service_unavailable', 'service unavailable');
  }
}

// Cron sweep: enumerate stale open holds via D1 (must SELECT user_id so we
// can route to the correct per-user DO), then refund each through the DO.
// 409 hold_already_settled = live debit/refund won the race; not an error.
// 503 / other = log and continue; the cron run is best-effort.
async function refundStaleHoldsViaDO(env: Env, thresholdMs: number): Promise<number> {
  const rows = await env.CREDIT_DB.prepare(
    "SELECT hold_id, user_id FROM credit_hold WHERE status='open' AND created_at < ? ORDER BY created_at LIMIT 500",
  ).bind(thresholdMs).all<{ hold_id: string; user_id: string }>();

  let refunded = 0;
  for (const row of rows.results) {
    const stub = env.CREDIT_DO.get(env.CREDIT_DO.idFromName(row.user_id));
    try {
      const resp = await stub.fetch('https://credit-do/api/billing/credit/refund', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-user-id': row.user_id },
        body: JSON.stringify({ holdId: row.hold_id }),
      });
      if (resp.status === 200) {
        refunded += 1;
      } else if (resp.status !== 409) {
        console.error(`[cron] refund ${row.hold_id} returned ${resp.status}`);
      }
    } catch (e) {
      console.error(`[cron] refund ${row.hold_id} threw:`, e);
    }
  }
  return refunded;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const ip = req.headers.get('cf-connecting-ip') ?? '0.0.0.0';

    if (url.pathname === '/api/billing/quota' && req.method === 'GET') {
      return Response.json(await readQuota(env.RATE_LIMIT_KV, ip));
    }
    if (url.pathname === '/api/billing/bump' && req.method === 'POST') {
      const used = await bumpQuota(env.RATE_LIMIT_KV, ip);
      return Response.json({ aiUsed: used });
    }

    if (url.pathname.startsWith('/api/billing/credit/')) {
      const userOrErr = requireUserId(req);
      if (userOrErr instanceof Response) return userOrErr;
      return proxyToCreditDO(url, req, env, userOrErr);
    }

    if (url.pathname === '/api/billing/checkout') return TODO('Creem cutover 2026-10');
    if (url.pathname === '/api/billing/webhook') return TODO('Creem cutover 2026-10');
    return new Response('not found', { status: 404 });
  },

  async scheduled(_event: ScheduledController, env: Env, _ctx: ExecutionContext): Promise<void> {
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    try {
      const n = await refundStaleHoldsViaDO(env, oneHourAgo);
      console.log(`[cron] refunded ${n} stale holds`);
    } catch (e) {
      console.error('[cron] refundStaleHoldsViaDO failed:', e);
      throw e;
    }
  },
};
