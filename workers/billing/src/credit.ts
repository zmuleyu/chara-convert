import type { BalanceView, HoldResponse, DebitResponse, RefundResponse } from './types';

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

export async function debit(
  db: D1Database,
  holdId: string,
  actualAmount: number,
): Promise<DebitResponse> {
  if (!Number.isInteger(actualAmount) || actualAmount < 0) {
    throw new Error('bad_request: actualAmount must be non-negative integer');
  }
  const h = await db
    .prepare('SELECT user_id, amount, status FROM credit_hold WHERE hold_id = ?')
    .bind(holdId)
    .first<{ user_id: string; amount: number; status: string }>();
  if (!h) throw new Error('hold_not_found');
  if (h.status !== 'open') throw new Error('hold_already_settled');

  const bal = await db
    .prepare('SELECT balance, held FROM credit_balance WHERE user_id = ?')
    .bind(h.user_id)
    .first<{ balance: number; held: number }>();
  const balance = bal?.balance ?? 0;
  const held = bal?.held ?? 0;

  const holdAmount = h.amount;
  const releaseFromHeld = Math.min(actualAmount, holdAmount);
  let extraFromBalance = Math.max(0, actualAmount - holdAmount);
  let overCap: string | null = null;
  if (extraFromBalance > balance) {
    extraFromBalance = balance;
    overCap = 'over_debit_capped';
  }
  const refundToBalance = holdAmount - releaseFromHeld;
  const now = Date.now();

  const newHeld = held - holdAmount;
  const newBalance = balance + refundToBalance - extraFromBalance;

  const stmts = [
    db.prepare(
      'UPDATE credit_balance SET balance = ?, held = ?, updated_at = ? WHERE user_id = ?',
    ).bind(newBalance, newHeld, now, h.user_id),
    db.prepare(
      "UPDATE credit_hold SET status = 'debited', settled_at = ? WHERE hold_id = ?",
    ).bind(now, holdId),
    db.prepare(
      "INSERT INTO credit_ledger (ts, user_id, delta, reason, hold_id, note) VALUES (?, ?, ?, 'debit', ?, ?)",
    ).bind(now, h.user_id, -(releaseFromHeld + extraFromBalance), holdId, overCap),
  ];
  if (refundToBalance > 0) {
    stmts.push(
      db.prepare(
        "INSERT INTO credit_ledger (ts, user_id, delta, reason, hold_id, note) VALUES (?, ?, ?, 'refund', ?, 'partial_unspent')",
      ).bind(now, h.user_id, refundToBalance, holdId),
    );
  }
  await db.batch(stmts);
  return { newBalance };
}

export async function refund(
  db: D1Database,
  holdId: string,
): Promise<RefundResponse> {
  const h = await db
    .prepare('SELECT user_id, amount, status FROM credit_hold WHERE hold_id = ?')
    .bind(holdId)
    .first<{ user_id: string; amount: number; status: string }>();
  if (!h) {
    return { newBalance: 0 };
  }
  if (h.status !== 'open') throw new Error('hold_already_settled');

  const bal = await db
    .prepare('SELECT balance, held FROM credit_balance WHERE user_id = ?')
    .bind(h.user_id)
    .first<{ balance: number; held: number }>();
  const balance = bal?.balance ?? 0;
  const held = bal?.held ?? 0;
  const now = Date.now();

  const newBalance = balance + h.amount;
  const newHeld = held - h.amount;

  await db.batch([
    db.prepare(
      'UPDATE credit_balance SET balance = ?, held = ?, updated_at = ? WHERE user_id = ?',
    ).bind(newBalance, newHeld, now, h.user_id),
    db.prepare(
      "UPDATE credit_hold SET status = 'refunded', settled_at = ? WHERE hold_id = ?",
    ).bind(now, holdId),
    db.prepare(
      "INSERT INTO credit_ledger (ts, user_id, delta, reason, hold_id) VALUES (?, ?, ?, 'refund', ?)",
    ).bind(now, h.user_id, h.amount, holdId),
  ]);

  return { newBalance };
}

export async function refundOpenHoldsOlderThan(
  db: D1Database,
  thresholdMs: number,
): Promise<number> {
  const rows = await db
    .prepare(
      "SELECT hold_id FROM credit_hold WHERE status='open' AND created_at < ? ORDER BY created_at LIMIT 500",
    )
    .bind(thresholdMs)
    .all<{ hold_id: string }>();
  let n = 0;
  for (const row of rows.results) {
    try {
      await refund(db, row.hold_id);
      n += 1;
    } catch {
      // race with concurrent debit — skip; next cron tick re-evaluates
    }
  }
  return n;
}
