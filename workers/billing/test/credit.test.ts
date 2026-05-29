import { describe, it, expect, beforeEach } from 'vitest';
import { env } from 'cloudflare:test';
import { applyMigration } from './helpers';
import { getBalance, hold, InsufficientCredit, debit, refund } from '../src/credit';

declare const __MIGRATION_SQL__: string;

beforeEach(() => applyMigration(__MIGRATION_SQL__));

describe('getBalance', () => {
  it('returns zero view for never-seen user', async () => {
    const v = await getBalance(env.CREDIT_DB, 'u-new');
    expect(v).toEqual({ balance: 0, held: 0 });
  });

  it('returns persisted values', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance (user_id, balance, held, updated_at) VALUES (?, ?, ?, ?)",
    ).bind('u-1', 500, 30, Date.now()).run();
    const v = await getBalance(env.CREDIT_DB, 'u-1');
    expect(v).toEqual({ balance: 500, held: 30 });
  });
});

describe('hold', () => {
  it('atomically moves credit balance → held and records ledger row', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance (user_id, balance, held, updated_at) VALUES ('u-2', 1000, 0, ?)",
    ).bind(Date.now()).run();

    const { holdId, newBalance } = await hold(env.CREDIT_DB, 'u-2', 300);

    expect(newBalance).toBe(700);
    expect(holdId).toMatch(/^h_[0-9a-z]+$/);

    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind('u-2').first();
    expect(bal).toEqual({ balance: 700, held: 300 });

    const ledger = await env.CREDIT_DB.prepare(
      "SELECT delta, reason FROM credit_ledger WHERE user_id='u-2'",
    ).all();
    expect(ledger.results).toEqual([{ delta: -300, reason: 'hold' }]);
  });

  it('throws InsufficientCredit when balance < amount, leaves state untouched', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance (user_id, balance, held, updated_at) VALUES ('u-3', 50, 0, ?)",
    ).bind(Date.now()).run();

    await expect(hold(env.CREDIT_DB, 'u-3', 100)).rejects.toBeInstanceOf(InsufficientCredit);

    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind('u-3').first();
    expect(bal).toEqual({ balance: 50, held: 0 });

    const ledger = await env.CREDIT_DB.prepare(
      "SELECT count(*) AS n FROM credit_ledger WHERE user_id='u-3'",
    ).first();
    expect(ledger).toEqual({ n: 0 });
  });

  it('auto-creates balance row at zero and rejects', async () => {
    await expect(hold(env.CREDIT_DB, 'u-fresh', 1)).rejects.toBeInstanceOf(InsufficientCredit);
  });
});

describe('debit', () => {
  it('settles hold with actual == held; balance unchanged, held -= amount', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-4', 700, 300, ?)",
    ).bind(Date.now()).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-test-1', 'u-4', 300, 'open', ?, NULL)",
    ).bind(Date.now()).run();

    const r = await debit(env.CREDIT_DB, 'h-test-1', 300);
    expect(r.newBalance).toBe(700);

    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind('u-4').first();
    expect(bal).toEqual({ balance: 700, held: 0 });

    const hold = await env.CREDIT_DB.prepare(
      'SELECT status FROM credit_hold WHERE hold_id=?',
    ).bind('h-test-1').first();
    expect(hold).toEqual({ status: 'debited' });
  });

  it('refunds difference when actual < hold amount', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-5', 500, 200, ?)",
    ).bind(Date.now()).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-test-2', 'u-5', 200, 'open', ?, NULL)",
    ).bind(Date.now()).run();

    const r = await debit(env.CREDIT_DB, 'h-test-2', 80);
    expect(r.newBalance).toBe(620);

    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind('u-5').first();
    expect(bal).toEqual({ balance: 620, held: 0 });
  });

  it('rejects unknown hold_id', async () => {
    await expect(debit(env.CREDIT_DB, 'h-nope', 50)).rejects.toThrow(/hold_not_found/);
  });

  it('rejects already-settled hold (idempotency check)', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-6', 100, 0, ?)",
    ).bind(Date.now()).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-done', 'u-6', 50, 'debited', ?, ?)",
    ).bind(Date.now(), Date.now()).run();

    await expect(debit(env.CREDIT_DB, 'h-done', 50)).rejects.toThrow(/hold_already_settled/);
  });

  it('caps over-debit at held amount + remaining balance and notes the cap', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-7', 20, 100, ?)",
    ).bind(Date.now()).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-over', 'u-7', 100, 'open', ?, NULL)",
    ).bind(Date.now()).run();

    const r = await debit(env.CREDIT_DB, 'h-over', 200);
    expect(r.newBalance).toBe(0);

    const ledger = await env.CREDIT_DB.prepare(
      "SELECT reason, delta, note FROM credit_ledger WHERE hold_id='h-over' ORDER BY ts",
    ).all();
    expect(ledger.results).toContainEqual(
      expect.objectContaining({ reason: 'debit', note: 'over_debit_capped' }),
    );
  });
});

describe('refund', () => {
  it('returns held amount to balance and marks hold refunded', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-8', 400, 150, ?)",
    ).bind(Date.now()).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-r-1', 'u-8', 150, 'open', ?, NULL)",
    ).bind(Date.now()).run();

    const r = await refund(env.CREDIT_DB, 'h-r-1');
    expect(r.newBalance).toBe(550);

    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind('u-8').first();
    expect(bal).toEqual({ balance: 550, held: 0 });

    const hold = await env.CREDIT_DB.prepare(
      'SELECT status FROM credit_hold WHERE hold_id=?',
    ).bind('h-r-1').first();
    expect(hold).toEqual({ status: 'refunded' });

    const ledger = await env.CREDIT_DB.prepare(
      "SELECT delta, reason FROM credit_ledger WHERE hold_id='h-r-1'",
    ).first();
    expect(ledger).toEqual({ delta: 150, reason: 'refund' });
  });

  it('is idempotent on unknown hold (no-op, returns current balance)', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-9', 90, 0, ?)",
    ).bind(Date.now()).run();
    const r = await refund(env.CREDIT_DB, 'h-missing');
    expect(r.newBalance).toBe(0);
  });

  it('rejects refund on already-debited hold', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-10', 100, 0, ?)",
    ).bind(Date.now()).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-debited', 'u-10', 50, 'debited', ?, ?)",
    ).bind(Date.now(), Date.now()).run();
    await expect(refund(env.CREDIT_DB, 'h-debited')).rejects.toThrow(/hold_already_settled/);
  });
});
