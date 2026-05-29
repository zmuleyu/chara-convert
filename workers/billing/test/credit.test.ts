import { describe, it, expect, beforeEach } from 'vitest';
import { env } from 'cloudflare:test';
import { applyMigration } from './helpers';
import { getBalance, hold, InsufficientCredit } from '../src/credit';

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
