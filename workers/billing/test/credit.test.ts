import { describe, it, expect, beforeEach } from 'vitest';
import { env } from 'cloudflare:test';
import { applyMigration } from './helpers';
import { getBalance } from '../src/credit';

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
