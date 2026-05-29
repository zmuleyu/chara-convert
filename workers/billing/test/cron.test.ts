import { describe, it, expect, beforeEach } from 'vitest';
import { env, createScheduledController, createExecutionContext, waitOnExecutionContext } from 'cloudflare:test';
import worker from '../src/index';
import { applyMigration } from './helpers';

declare const __MIGRATION_SQL__: string;

beforeEach(() => applyMigration(__MIGRATION_SQL__));

describe('scheduled', () => {
  it('refunds holds older than one hour, leaves fresh ones alone', async () => {
    const now = Date.now();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-cron', 0, 200, ?)",
    ).bind(now).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-stale', 'u-cron', 200, 'open', ?, NULL)",
    ).bind(now - 2 * 60 * 60 * 1000).run();

    const ctrl = createScheduledController({ scheduledTime: new Date(now), cron: '*/10 * * * *' });
    const ctx = createExecutionContext();
    await worker.scheduled!(ctrl, env, ctx);
    await waitOnExecutionContext(ctx);

    const h = await env.CREDIT_DB.prepare(
      "SELECT status FROM credit_hold WHERE hold_id='h-stale'",
    ).first();
    expect(h).toEqual({ status: 'refunded' });

    const bal = await env.CREDIT_DB.prepare(
      "SELECT balance, held FROM credit_balance WHERE user_id='u-cron'",
    ).first();
    expect(bal).toEqual({ balance: 200, held: 0 });
  });
});
