import { describe, it, expect, beforeEach } from 'vitest';
import { SELF, env } from 'cloudflare:test';
import { applyMigration } from './helpers';
import { hold, debit, refund } from '../src/credit';

declare const __MIGRATION_SQL__: string;

beforeEach(() => applyMigration(__MIGRATION_SQL__));

// NOTE: migrations/0001_credit_ledger.sql comments "Invariant 1" as
// sum(ledger.delta) == balance + held, but that wording is inaccurate for the
// shipped impl: `hold` and `refund` rows record internal balance<->held
// transfers (non-zero delta with zero net effect on balance+held). The real
// external-conservation law is over the {grant, topup, debit} subset only —
// i.e. money entering (grant/topup) minus money leaving (debit) == b+h.
// We verify that here, plus invariant 3 (balance, held >= 0).
describe('conservation: sum(delta where reason in grant/topup/debit) == balance + held', () => {
  it('holds for 50 random operations on one user', async () => {
    const uid = 'u-inv';
    const seed = 10_000;
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES (?, ?, 0, ?)",
    ).bind(uid, seed, Date.now()).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_ledger (ts, user_id, delta, reason) VALUES (?, ?, ?, 'grant')",
    ).bind(Date.now(), uid, seed).run();

    const openHolds: string[] = [];
    for (let i = 0; i < 50; i++) {
      const r = Math.random();
      try {
        if (r < 0.5 || openHolds.length === 0) {
          const amount = 1 + Math.floor(Math.random() * 200);
          const { holdId } = await hold(env.CREDIT_DB, uid, amount);
          openHolds.push(holdId);
        } else if (r < 0.8) {
          const holdId = openHolds.shift()!;
          const actual = Math.floor(Math.random() * 200);
          await debit(env.CREDIT_DB, holdId, actual);
        } else {
          const holdId = openHolds.shift()!;
          await refund(env.CREDIT_DB, holdId);
        }
      } catch {
        // InsufficientCredit etc — invariant must still hold
      }
    }

    const sum = await env.CREDIT_DB.prepare(
      "SELECT COALESCE(SUM(delta),0) AS s FROM credit_ledger WHERE user_id=? AND reason IN ('grant','topup','debit')",
    ).bind(uid).first<{ s: number }>();
    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind(uid).first<{ balance: number; held: number }>();

    expect(sum!.s).toBe(bal!.balance + bal!.held);
    expect(bal!.balance).toBeGreaterThanOrEqual(0);
    expect(bal!.held).toBeGreaterThanOrEqual(0);
  });
});

// T17: same conservation/non-negative invariants under HTTP→CreditDO routing,
// with concurrent Promise.all bursts injected. The serial fuzzer above would
// pass even if blockConcurrencyWhile were removed (no concurrency), so this
// block is the regression net for DO serialization. shift() runs before the
// first await, so distinct burst-ops never collide on the same holdId — what
// we exercise is the cross-hold balance arithmetic under concurrent load.
describe('conservation under concurrent bursts (HTTP→CreditDO path)', () => {
  it('holds over 60 random ops with bursts of 2-5', async () => {
    const uid = 'u-inv-burst';
    const seed = 50_000;
    const now = Date.now();
    await env.CREDIT_DB.prepare(
      'INSERT INTO credit_balance VALUES (?, ?, 0, ?)',
    ).bind(uid, seed, now).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_ledger (ts, user_id, delta, reason) VALUES (?, ?, ?, 'grant')",
    ).bind(now, uid, seed).run();

    async function post(path: string, body: unknown): Promise<Response> {
      return SELF.fetch(`https://x${path}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-user-id': uid },
        body: JSON.stringify(body),
      });
    }

    const openHolds: string[] = [];

    async function runOne(): Promise<void> {
      const r = Math.random();
      if (r < 0.5 || openHolds.length === 0) {
        const amount = 1 + Math.floor(Math.random() * 200);
        const resp = await post('/api/billing/credit/hold', { amount });
        if (resp.status === 200) {
          const body = (await resp.json()) as { holdId: string };
          openHolds.push(body.holdId);
        }
      } else if (r < 0.8) {
        const holdId = openHolds.shift()!;
        const actual = Math.floor(Math.random() * 200);
        await post('/api/billing/credit/debit', { holdId, actualAmount: actual });
      } else {
        const holdId = openHolds.shift()!;
        await post('/api/billing/credit/refund', { holdId });
      }
    }

    let ops = 0;
    while (ops < 60) {
      if (Math.random() < 0.3) {
        const size = 2 + Math.floor(Math.random() * 4); // 2-5
        await Promise.all(Array.from({ length: size }, () => runOne()));
        ops += size;
      } else {
        await runOne();
        ops += 1;
      }
    }

    const sum = await env.CREDIT_DB.prepare(
      "SELECT COALESCE(SUM(delta),0) AS s FROM credit_ledger WHERE user_id=? AND reason IN ('grant','topup','debit')",
    ).bind(uid).first<{ s: number }>();
    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind(uid).first<{ balance: number; held: number }>();

    expect(sum!.s).toBe(bal!.balance + bal!.held);
    expect(bal!.balance).toBeGreaterThanOrEqual(0);
    expect(bal!.held).toBeGreaterThanOrEqual(0);
  });
});
