// T13 [Phase A.1] Concurrency race tests for tickets A.1-1 / A.1-2.
//
// Test disposition (post-T15, after CreditDO + blockConcurrencyWhile landed):
//
//   All 3 tests now pass deterministically because CreditDO's
//   `ctx.blockConcurrencyWhile(...)` makes each fetch handler a true critical
//   section per user_id. Any regression that removes the blockConcurrencyWhile
//   wrapper (or breaks proxy routing in index.ts) re-exposes the races:
//     - race-1 fires reliably (~30% per iter)
//     - race-2 fires occasionally (1 in 40 iters observed during T15 debug)
//     - race-3 fires occasionally
//   The N-iteration loops amplify trigger probability so the test fails loudly
//   on the next CI run rather than waiting for prod to expose the bug.
//
// Spec: docs/specs/2026-05-30-credit-router-phase-A1-races.md

import { SELF, env } from 'cloudflare:test';
import { describe, it, expect, beforeEach } from 'vitest';
import { applyMigration } from './helpers';

declare const __MIGRATION_SQL__: string;

beforeEach(() => applyMigration(__MIGRATION_SQL__));

const ITERATIONS = 15;
const ITERATIONS_HEAVY = 40;

async function post(path: string, userId: string, body: unknown): Promise<Response> {
  return SELF.fetch(`https://x${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-user-id': userId },
    body: JSON.stringify(body),
  });
}

describe('A.1-1 concurrent hold (serialized by CreditDO)', () => {
  it('5 concurrent hold(50) against balance=100 yields exactly 2 successes, balance never negative', async () => {
    const violations: string[] = [];
    for (let i = 0; i < ITERATIONS; i++) {
      const uid = `u-race-1-${i}`;
      await env.CREDIT_DB.prepare(
        'INSERT INTO credit_balance (user_id, balance, held, updated_at) VALUES (?, 100, 0, ?)',
      ).bind(uid, Date.now()).run();

      const responses = await Promise.all(
        Array.from({ length: 5 }, () => post('/api/billing/credit/hold', uid, { amount: 50 })),
      );
      const successes = responses.filter(r => r.status === 200).length;
      const insufficient = responses.filter(r => r.status === 402).length;
      const final = await env.CREDIT_DB.prepare(
        'SELECT balance, held FROM credit_balance WHERE user_id=?',
      ).bind(uid).first<{ balance: number; held: number }>();

      if (successes !== 2 || insufficient !== 3) {
        violations.push(`iter ${i}: successes=${successes} insufficient=${insufficient}`);
      } else if (final!.balance < 0 || final!.balance + final!.held !== 100) {
        violations.push(`iter ${i}: balance=${final!.balance} held=${final!.held}`);
      }
    }
    expect(violations, `race triggered in ${violations.length}/${ITERATIONS} iterations: ${violations.join(' | ')}`).toEqual([]);
  });
});

describe('A.1-2 concurrent debit on same hold (serialized by CreditDO)', () => {
  it('3 concurrent debit(holdId, 200) yields exactly 1 success and 1 debit ledger row', async () => {
    const violations: string[] = [];
    for (let i = 0; i < ITERATIONS_HEAVY; i++) {
      const uid = `u-race-2-${i}`;
      const hid = `h-race-2-${i}`;
      const now = Date.now();
      await env.CREDIT_DB.prepare('INSERT INTO credit_balance VALUES (?, 700, 300, ?)').bind(uid, now).run();
      await env.CREDIT_DB.prepare("INSERT INTO credit_hold VALUES (?, ?, 300, 'open', ?, NULL)").bind(hid, uid, now).run();

      const responses = await Promise.all(
        Array.from({ length: 3 }, () =>
          post('/api/billing/credit/debit', uid, { holdId: hid, actualAmount: 200 }),
        ),
      );
      const statuses = responses.map(r => r.status).sort();
      const debitRows = await env.CREDIT_DB.prepare(
        "SELECT count(*) AS n FROM credit_ledger WHERE hold_id=? AND reason='debit'",
      ).bind(hid).first<{ n: number }>();

      if (JSON.stringify(statuses) !== '[200,409,409]' || debitRows!.n !== 1) {
        violations.push(`iter ${i}: statuses=${JSON.stringify(statuses)} debitRows=${debitRows!.n}`);
      }
    }
    expect(violations, `race triggered in ${violations.length} iterations: ${violations.join(' | ')}`).toEqual([]);
  });
});

describe('A.1-2 concurrent debit + refund on same hold (serialized by CreditDO)', () => {
  it('1 debit + 1 refund concurrent: exactly one wins (200), the other returns 409', async () => {
    const violations: string[] = [];
    for (let i = 0; i < ITERATIONS_HEAVY; i++) {
      const uid = `u-race-3-${i}`;
      const hid = `h-race-3-${i}`;
      const now = Date.now();
      await env.CREDIT_DB.prepare('INSERT INTO credit_balance VALUES (?, 600, 400, ?)').bind(uid, now).run();
      await env.CREDIT_DB.prepare("INSERT INTO credit_hold VALUES (?, ?, 400, 'open', ?, NULL)").bind(hid, uid, now).run();

      const [debitR, refundR] = await Promise.all([
        post('/api/billing/credit/debit', uid, { holdId: hid, actualAmount: 400 }),
        post('/api/billing/credit/refund', uid, { holdId: hid }),
      ]);
      const statuses = [debitR.status, refundR.status].sort();
      const settlementRows = await env.CREDIT_DB.prepare(
        "SELECT count(*) AS n FROM credit_ledger WHERE hold_id=? AND reason IN ('debit','refund')",
      ).bind(hid).first<{ n: number }>();

      if (JSON.stringify(statuses) !== '[200,409]' || settlementRows!.n !== 1) {
        violations.push(`iter ${i}: statuses=${JSON.stringify(statuses)} settlementRows=${settlementRows!.n}`);
      }
    }
    expect(violations, `race triggered in ${violations.length} iterations: ${violations.join(' | ')}`).toEqual([]);
  });
});
