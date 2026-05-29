// CreditDO — per-user Durable Object serializing all credit mutations for a
// single user_id. Phase A.1 fix for race tickets A.1-1 and A.1-2.
//
// Instance routing: env.CREDIT_DO.idFromName(user_id) — exactly one DO per
// user_id. The DO trusts the incoming x-user-id header (Worker has already
// validated it).
//
// Persistence: D1 (this.env.CREDIT_DB). DO storage is intentionally unused.
//
// Concurrency model: DOs do NOT serialize concurrent fetch() requests by
// default — `await` on external I/O (D1, outbound fetch) releases the input
// gate and the runtime can dispatch another in-flight request. We therefore
// wrap the entire credit handler body in `ctx.blockConcurrencyWhile(...)` to
// create a true critical section per DO instance (per user_id). Inside the
// callback, awaits still yield, but no NEW fetch handler is dispatched until
// the callback returns. See race tests in test/race.test.ts.
//
// Spec: docs/specs/2026-05-30-credit-router-phase-A1-races.md

import { DurableObject } from 'cloudflare:workers';
import { getBalance, hold, debit, refund, InsufficientCredit } from './credit';
import type { Env, CreditError } from './types';

function ok<T>(body: T): Response {
  return new Response(JSON.stringify(body), {
    status: 200, headers: { 'content-type': 'application/json' },
  });
}

function err(status: number, code: CreditError['code'], message: string): Response {
  const body: CreditError = { code, message };
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  });
}

export class CreditDO extends DurableObject<Env> {
  override async fetch(req: Request): Promise<Response> {
    const url = new URL(req.url);
    const userId = req.headers.get('x-user-id');
    if (!userId) return err(400, 'missing_user_id', 'X-User-Id header is required');

    // Pre-parse the body OUTSIDE the critical section — reading the request
    // stream is per-request state and can race-safely happen in parallel.
    let body: Record<string, unknown> | undefined;
    if (req.method === 'POST') {
      try {
        body = await req.json<Record<string, unknown>>();
      } catch {
        return err(400, 'bad_request', 'invalid JSON body');
      }
    }

    return this.ctx.blockConcurrencyWhile(async () => {
      if (url.pathname === '/api/billing/credit/balance' && req.method === 'GET') {
        return ok(await getBalance(this.env.CREDIT_DB, userId));
      }
      if (url.pathname === '/api/billing/credit/hold' && req.method === 'POST') {
        if (typeof body!.amount !== 'number') return err(400, 'bad_request', 'amount: number required');
        try {
          return ok(await hold(this.env.CREDIT_DB, userId, body!.amount));
        } catch (e) {
          if (e instanceof InsufficientCredit) return err(402, 'insufficient_credit', 'balance < amount');
          console.error('CreditDO hold unexpected:', e);
          return err(500, 'internal_error', 'internal error');
        }
      }
      if (url.pathname === '/api/billing/credit/debit' && req.method === 'POST') {
        if (typeof body!.holdId !== 'string' || typeof body!.actualAmount !== 'number') {
          return err(400, 'bad_request', 'holdId: string, actualAmount: number required');
        }
        try {
          return ok(await debit(this.env.CREDIT_DB, body!.holdId, body!.actualAmount));
        } catch (e) {
          const m = (e as Error).message;
          if (m === 'hold_not_found') return err(404, 'hold_not_found', m);
          if (m === 'hold_already_settled') return err(409, 'hold_already_settled', m);
          console.error('CreditDO debit unexpected:', e);
          return err(500, 'internal_error', 'internal error');
        }
      }
      if (url.pathname === '/api/billing/credit/refund' && req.method === 'POST') {
        if (typeof body!.holdId !== 'string') return err(400, 'bad_request', 'holdId: string required');
        try {
          return ok(await refund(this.env.CREDIT_DB, body!.holdId));
        } catch (e) {
          const m = (e as Error).message;
          if (m === 'hold_already_settled') return err(409, 'hold_already_settled', m);
          console.error('CreditDO refund unexpected:', e);
          return err(500, 'internal_error', 'internal error');
        }
      }
      return err(404, 'not_found', 'unknown op');
    });
  }
}
