import { readQuota, bumpQuota } from './quota';
import { getBalance, hold, debit, refund, InsufficientCredit, refundOpenHoldsOlderThan } from './credit';
import type { Env, CreditError } from './types';

const TODO = (todo: string) => new Response(JSON.stringify({ todo }), {
  status: 501, headers: { 'content-type': 'application/json' },
});

function err(status: number, code: CreditError['code'], message: string): Response {
  const body: CreditError = { code, message };
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  });
}

function ok<T>(body: T): Response {
  return new Response(JSON.stringify(body), {
    status: 200, headers: { 'content-type': 'application/json' },
  });
}

function requireUserId(req: Request): string | Response {
  const u = req.headers.get('x-user-id');
  if (!u) return err(400, 'missing_user_id', 'X-User-Id header is required');
  return u;
}

async function handleCredit(url: URL, req: Request, env: Env): Promise<Response | null> {
  const userOrErr = requireUserId(req);
  if (userOrErr instanceof Response) return userOrErr;
  const userId = userOrErr;

  if (url.pathname === '/api/billing/credit/balance' && req.method === 'GET') {
    return ok(await getBalance(env.CREDIT_DB, userId));
  }
  if (url.pathname === '/api/billing/credit/hold' && req.method === 'POST') {
    const body = await req.json<{ amount?: unknown }>();
    if (typeof body.amount !== 'number') return err(400, 'bad_request', 'amount: number required');
    try {
      return ok(await hold(env.CREDIT_DB, userId, body.amount));
    } catch (e) {
      if (e instanceof InsufficientCredit) return err(402, 'insufficient_credit', 'balance < amount');
      throw e;
    }
  }
  if (url.pathname === '/api/billing/credit/debit' && req.method === 'POST') {
    const body = await req.json<{ holdId?: unknown; actualAmount?: unknown }>();
    if (typeof body.holdId !== 'string' || typeof body.actualAmount !== 'number') {
      return err(400, 'bad_request', 'holdId: string, actualAmount: number required');
    }
    try {
      return ok(await debit(env.CREDIT_DB, body.holdId, body.actualAmount));
    } catch (e) {
      const m = (e as Error).message;
      if (m === 'hold_not_found') return err(404, 'hold_not_found', m);
      if (m === 'hold_already_settled') return err(409, 'hold_already_settled', m);
      throw e;
    }
  }
  if (url.pathname === '/api/billing/credit/refund' && req.method === 'POST') {
    const body = await req.json<{ holdId?: unknown }>();
    if (typeof body.holdId !== 'string') return err(400, 'bad_request', 'holdId: string required');
    try {
      return ok(await refund(env.CREDIT_DB, body.holdId));
    } catch (e) {
      const m = (e as Error).message;
      if (m === 'hold_already_settled') return err(409, 'hold_already_settled', m);
      throw e;
    }
  }
  return null;
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
      const r = await handleCredit(url, req, env);
      if (r) return r;
    }

    if (url.pathname === '/api/billing/checkout') return TODO('Creem cutover 2026-10');
    if (url.pathname === '/api/billing/webhook') return TODO('Creem cutover 2026-10');
    return new Response('not found', { status: 404 });
  },

  async scheduled(_event: ScheduledController, env: Env, _ctx: ExecutionContext): Promise<void> {
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    await refundOpenHoldsOlderThan(env.CREDIT_DB, oneHourAgo);
  },
};
