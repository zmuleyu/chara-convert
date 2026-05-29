import { defineWorkersConfig } from '@cloudflare/vitest-pool-workers/config';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const migrationSql = readFileSync(
  join(__dirname, 'migrations', '0001_credit_ledger.sql'),
  'utf8',
);

export default defineWorkersConfig({
  define: {
    __MIGRATION_SQL__: JSON.stringify(migrationSql),
  },
  test: {
    poolOptions: {
      workers: {
        wrangler: { configPath: './wrangler.toml' },
        miniflare: {
          d1Databases: ['CREDIT_DB'],
          d1Persist: false,
          kvNamespaces: ['RATE_LIMIT_KV'],
        },
      },
    },
  },
});
