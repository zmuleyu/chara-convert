import { env } from 'cloudflare:test';

// Drop-then-create so tests stay deterministic under isolatedStorage:false
// (each beforeEach gets a fresh schema and zero rows).
const TABLES = ['credit_balance', 'credit_hold', 'credit_ledger'];

export async function applyMigration(sql: string): Promise<void> {
  for (const t of TABLES) {
    await env.CREDIT_DB.prepare(`DROP TABLE IF EXISTS ${t}`).run();
  }
  const sqlNoComments = sql
    .split('\n')
    .filter(l => !l.trim().startsWith('--'))
    .join('\n');
  for (const stmt of sqlNoComments.split(';').map(s => s.trim()).filter(Boolean)) {
    await env.CREDIT_DB.prepare(stmt).run();
  }
}
