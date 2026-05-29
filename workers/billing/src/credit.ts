import type { BalanceView, HoldResponse } from './types';

export async function getBalance(db: D1Database, userId: string): Promise<BalanceView> {
  const row = await db
    .prepare('SELECT balance, held FROM credit_balance WHERE user_id = ?')
    .bind(userId)
    .first<{ balance: number; held: number }>();
  return row ? { balance: row.balance, held: row.held } : { balance: 0, held: 0 };
}

export class InsufficientCredit extends Error {
  constructor() { super('insufficient_credit'); this.name = 'InsufficientCredit'; }
}

function newHoldId(): string {
  return 'h_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

export async function hold(
  db: D1Database,
  userId: string,
  amount: number,
): Promise<HoldResponse> {
  if (!Number.isInteger(amount) || amount <= 0) {
    throw new Error('bad_request: amount must be positive integer');
  }
  const now = Date.now();
  const holdId = newHoldId();

  const bal = await db
    .prepare('SELECT balance, held FROM credit_balance WHERE user_id = ?')
    .bind(userId)
    .first<{ balance: number; held: number }>();
  const balance = bal?.balance ?? 0;
  if (balance < amount) throw new InsufficientCredit();

  const upsertBalance = bal
    ? db.prepare(
        'UPDATE credit_balance SET balance = balance - ?, held = held + ?, updated_at = ? WHERE user_id = ?',
      ).bind(amount, amount, now, userId)
    : db.prepare(
        'INSERT INTO credit_balance (user_id, balance, held, updated_at) VALUES (?, ?, ?, ?)',
      ).bind(userId, -amount, amount, now);

  const insertHold = db.prepare(
    "INSERT INTO credit_hold (hold_id, user_id, amount, status, created_at) VALUES (?, ?, ?, 'open', ?)",
  ).bind(holdId, userId, amount, now);

  const insertLedger = db.prepare(
    "INSERT INTO credit_ledger (ts, user_id, delta, reason, hold_id) VALUES (?, ?, ?, 'hold', ?)",
  ).bind(now, userId, -amount, holdId);

  await db.batch([upsertBalance, insertHold, insertLedger]);
  return { holdId, newBalance: balance - amount };
}
