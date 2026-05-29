import { env } from 'cloudflare:test';

export async function applyMigration(sql: string): Promise<void> {
  const sqlNoComments = sql
    .split('\n')
    .filter(l => !l.trim().startsWith('--'))
    .join('\n');
  for (const stmt of sqlNoComments.split(';').map(s => s.trim()).filter(Boolean)) {
    await env.CREDIT_DB.prepare(stmt).run();
  }
}
