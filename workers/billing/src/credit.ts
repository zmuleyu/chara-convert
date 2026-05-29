import type { BalanceView } from './types';

export async function getBalance(db: D1Database, userId: string): Promise<BalanceView> {
  const row = await db
    .prepare('SELECT balance, held FROM credit_balance WHERE user_id = ?')
    .bind(userId)
    .first<{ balance: number; held: number }>();
  return row ? { balance: row.balance, held: row.held } : { balance: 0, held: 0 };
}
