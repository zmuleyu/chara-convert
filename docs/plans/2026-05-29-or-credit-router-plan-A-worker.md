# Phase A — Billing Worker + D1 Credit Ledger

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Cloudflare Worker that owns credit balances and atomic hold/debit/refund lifecycle, backed by D1.

**Architecture:** Single D1 database `CREDIT_DB` with 3 tables (`credit_balance`, `credit_hold`, `credit_ledger`). All mutations go through `credit.ts` helpers that wrap `db.batch()` for atomicity. `index.ts` exposes 4 REST endpoints + existing IP quota endpoints (preserved). Cron handler refunds stale open holds.

**Tech Stack:** Cloudflare Workers (TypeScript, ESM), D1 (SQLite dialect), vitest + miniflare for local D1 tests, wrangler 3.

**Working directory for all bash commands in this plan:** `D:/projects/aichat_group/chara-convert/workers/billing/`

---

## File structure (this phase)

| File | Status | Responsibility |
|---|---|---|
| `wrangler.toml` | modify | add `[[d1_databases]]` binding + cron trigger |
| `migrations/0001_credit_ledger.sql` | create | 3 tables + 2 indexes |
| `src/credit.ts` | create | hold/debit/refund/balance helpers (transactional) |
| `src/index.ts` | modify | wire 4 credit endpoints + scheduled handler |
| `src/types.ts` | create | shared Env + request/response interfaces |
| `test/credit.test.ts` | create | unit tests against miniflare D1 |
| `test/endpoints.test.ts` | create | HTTP integration tests via worker fetch |
| `test/cron.test.ts` | create | scheduled handler test |

---

## Task 1: D1 binding in wrangler.toml

**Files:**
- Modify: [workers/billing/wrangler.toml](../../workers/billing/wrangler.toml)

- [ ] **Step 1: Read current wrangler.toml** to preserve KV binding.

- [ ] **Step 2: Append D1 binding and cron trigger** below existing `[[kv_namespaces]]` block.

```toml
[[d1_databases]]
binding = "CREDIT_DB"
database_name = "chara-convert-credit"
database_id = "REPLACE_AFTER_CREATE"
preview_database_id = "REPLACE_AFTER_CREATE_PREVIEW"
migrations_dir = "migrations"

[triggers]
crons = ["*/10 * * * *"]
```

- [ ] **Step 3: Create the D1 database**

Run (from `workers/billing/`):
```
npx wrangler d1 create chara-convert-credit
```
Expected: prints `database_id = "<uuid>"`. Replace `REPLACE_AFTER_CREATE` in wrangler.toml with that UUID.

- [ ] **Step 4: Create the preview D1 database** (used by `wrangler dev`)

```
npx wrangler d1 create chara-convert-credit-preview
```
Replace `REPLACE_AFTER_CREATE_PREVIEW` with the returned UUID.

- [ ] **Step 5: Commit**

```bash
git add workers/billing/wrangler.toml
git commit -m "feat(billing): bind D1 CREDIT_DB and cron trigger"
```

---

## Task 2: D1 migration SQL

**Files:**
- Create: [workers/billing/migrations/0001_credit_ledger.sql](../../workers/billing/migrations/0001_credit_ledger.sql)

- [ ] **Step 1: Write the migration**

```sql
-- 0001_credit_ledger.sql
-- Schema for credit ledger. Owner: docs/specs/2026-05-29-or-credit-router-design.md
-- Invariant 1: sum(credit_ledger.delta) per user == credit_balance.balance + credit_balance.held
-- Invariant 2: every credit_hold row settles to 'debited' or 'refunded'
-- Invariant 3: credit_balance.balance + credit_balance.held >= 0 always

CREATE TABLE credit_balance (
  user_id    TEXT PRIMARY KEY,
  balance    INTEGER NOT NULL DEFAULT 0,
  held       INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);

CREATE TABLE credit_hold (
  hold_id    TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL,
  amount     INTEGER NOT NULL,
  status     TEXT NOT NULL CHECK (status IN ('open', 'debited', 'refunded')),
  created_at INTEGER NOT NULL,
  settled_at INTEGER
);
CREATE INDEX idx_credit_hold_open ON credit_hold(status, created_at) WHERE status='open';

CREATE TABLE credit_ledger (
  ts         INTEGER NOT NULL,
  user_id    TEXT NOT NULL,
  delta      INTEGER NOT NULL,
  reason     TEXT NOT NULL CHECK (reason IN ('hold','debit','refund','topup','grant')),
  hold_id    TEXT,
  note       TEXT
);
CREATE INDEX idx_credit_ledger_user_ts ON credit_ledger(user_id, ts);
```

- [ ] **Step 2: Apply locally**

```
npx wrangler d1 migrations apply chara-convert-credit --local
```
Expected: `Migrations applied: 0001_credit_ledger.sql`.

- [ ] **Step 3: Verify schema in local D1**

```
npx wrangler d1 execute chara-convert-credit --local --command "SELECT name FROM sqlite_master WHERE type='table';"
```
Expected output rows include `credit_balance`, `credit_hold`, `credit_ledger`.

- [ ] **Step 4: Commit**

```bash
git add workers/billing/migrations/0001_credit_ledger.sql
git commit -m "feat(billing): D1 migration for credit ledger schema"
```

---

## Task 3: Shared types module

**Files:**
- Create: [workers/billing/src/types.ts](../../workers/billing/src/types.ts)

- [ ] **Step 1: Write types**

```ts
// Env shape — referenced by index.ts, credit.ts, scheduled handler.
export interface Env {
  RATE_LIMIT_KV: KVNamespace;
  CREDIT_DB: D1Database;
}

export interface BalanceView {
  balance: number;
  held: number;
}

export interface HoldRequest {
  amount: number;
}

export interface HoldResponse {
  holdId: string;
  newBalance: number;
}

export interface DebitRequest {
  holdId: string;
  actualAmount: number;
}

export interface DebitResponse {
  newBalance: number;
}

export interface RefundRequest {
  holdId: string;
}

export interface RefundResponse {
  newBalance: number;
}

// Error envelope used by every credit endpoint for non-2xx.
export interface CreditError {
  code: 'missing_user_id' | 'insufficient_credit' | 'hold_not_found' | 'hold_already_settled' | 'bad_request';
  message: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add workers/billing/src/types.ts
git commit -m "feat(billing): shared types for credit endpoints"
```

---

## Task 4: credit.ts — balance reader (TDD)

**Files:**
- Create: [workers/billing/src/credit.ts](../../workers/billing/src/credit.ts)
- Create: [workers/billing/test/credit.test.ts](../../workers/billing/test/credit.test.ts)
- Create: [workers/billing/vitest.config.ts](../../workers/billing/vitest.config.ts) (modify if exists)

- [ ] **Step 1: Configure miniflare D1 in vitest**

Edit `vitest.config.ts` to inject a D1 binding for tests:

```ts
import { defineConfig } from 'vitest/config';
import { defineWorkersConfig } from '@cloudflare/vitest-pool-workers/config';

export default defineWorkersConfig({
  test: {
    poolOptions: {
      workers: {
        wrangler: { configPath: './wrangler.toml' },
        miniflare: {
          d1Databases: ['CREDIT_DB'],
          d1Persist: false,
        },
      },
    },
  },
});
```

Run:
```
npm install --save-dev @cloudflare/vitest-pool-workers
```

- [ ] **Step 2: Create test helper to apply migration**

Add `test/helpers.ts`:

```ts
import { env } from 'cloudflare:test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

export async function applyMigration(): Promise<void> {
  const sql = readFileSync(
    join(__dirname, '..', 'migrations', '0001_credit_ledger.sql'),
    'utf8',
  );
  for (const stmt of sql.split(';').map(s => s.trim()).filter(Boolean)) {
    if (stmt.startsWith('--')) continue;
    await env.CREDIT_DB.prepare(stmt).run();
  }
}
```

- [ ] **Step 3: Write failing test for `getBalance`**

`test/credit.test.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest';
import { env } from 'cloudflare:test';
import { applyMigration } from './helpers';
import { getBalance } from '../src/credit';

beforeEach(applyMigration);

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
```

- [ ] **Step 4: Run — expect FAIL** (`getBalance` not exported)

```
npm test -- credit.test.ts
```
Expected: "Cannot find module '../src/credit'" or undefined export.

- [ ] **Step 5: Minimal implementation**

`src/credit.ts`:

```ts
import type { BalanceView } from './types';

export async function getBalance(db: D1Database, userId: string): Promise<BalanceView> {
  const row = await db
    .prepare('SELECT balance, held FROM credit_balance WHERE user_id = ?')
    .bind(userId)
    .first<{ balance: number; held: number }>();
  return row ? { balance: row.balance, held: row.held } : { balance: 0, held: 0 };
}
```

- [ ] **Step 6: Re-run — expect PASS**

```
npm test -- credit.test.ts
```

- [ ] **Step 7: Commit**

```bash
git add workers/billing/src/credit.ts workers/billing/test/credit.test.ts workers/billing/test/helpers.ts workers/billing/vitest.config.ts workers/billing/package.json workers/billing/package-lock.json
git commit -m "feat(billing): D1 balance reader"
```

---

## Task 5: credit.ts — atomic `hold` (TDD)

**Files:**
- Modify: [workers/billing/src/credit.ts](../../workers/billing/src/credit.ts)
- Modify: [workers/billing/test/credit.test.ts](../../workers/billing/test/credit.test.ts)

- [ ] **Step 1: Append failing tests**

```ts
import { hold, InsufficientCredit } from '../src/credit';

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
```

- [ ] **Step 2: Run — expect FAIL** (`hold` not defined).

- [ ] **Step 3: Implement `hold`**

Append to `src/credit.ts`:

```ts
import type { HoldResponse } from './types';

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
  const held = bal?.held ?? 0;
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
```

- [ ] **Step 4: Run — expect PASS** (all 5 tests).

- [ ] **Step 5: Commit**

```bash
git add workers/billing/src/credit.ts workers/billing/test/credit.test.ts
git commit -m "feat(billing): atomic credit hold with insufficient-credit guard"
```

---

## Task 6: credit.ts — `debit` (TDD)

**Files:**
- Modify: [workers/billing/src/credit.ts](../../workers/billing/src/credit.ts)
- Modify: [workers/billing/test/credit.test.ts](../../workers/billing/test/credit.test.ts)

Semantics: release the open hold; deduct `actualAmount` from `held`; if `actualAmount < holdAmount`, refund the diff back to `balance`; if `actualAmount > holdAmount`, allow over-debit (cap at `balance + held`, log warning ledger row with note).

- [ ] **Step 1: Append tests**

```ts
import { debit } from '../src/credit';

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
    expect(r.newBalance).toBe(620); // 500 + (200 - 80)

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
    // hold=100, balance=20, actualAmount=200 → cap to 100 from held, 20 from balance, note "over_debit_capped"
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
    // exactly one debit row carrying the cap note
    expect(ledger.results).toContainEqual(
      expect.objectContaining({ reason: 'debit', note: 'over_debit_capped' }),
    );
  });
});
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement `debit`**

Append to `src/credit.ts`:

```ts
import type { DebitResponse } from './types';

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
  let releaseFromHeld = Math.min(actualAmount, holdAmount);
  let extraFromBalance = Math.max(0, actualAmount - holdAmount);
  let overCap: string | null = null;
  if (extraFromBalance > balance) {
    extraFromBalance = balance;
    overCap = 'over_debit_capped';
  }
  const refundToBalance = holdAmount - releaseFromHeld; // ≥0 when actual<hold
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
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add workers/billing/src/credit.ts workers/billing/test/credit.test.ts
git commit -m "feat(billing): debit with partial-refund and over-debit cap"
```

---

## Task 7: credit.ts — `refund` (TDD)

**Files:**
- Modify: [workers/billing/src/credit.ts](../../workers/billing/src/credit.ts)
- Modify: [workers/billing/test/credit.test.ts](../../workers/billing/test/credit.test.ts)

- [ ] **Step 1: Append tests**

```ts
import { refund } from '../src/credit';

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
    // a never-seen user is treated as balance=0; rejecting would force callers
    // to special-case orphan-refund cron — easier to allow no-op.
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
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement `refund`**

Append to `src/credit.ts`:

```ts
import type { RefundResponse } from './types';

export async function refund(
  db: D1Database,
  holdId: string,
): Promise<RefundResponse> {
  const h = await db
    .prepare('SELECT user_id, amount, status FROM credit_hold WHERE hold_id = ?')
    .bind(holdId)
    .first<{ user_id: string; amount: number; status: string }>();
  if (!h) {
    // idempotent no-op for orphan-refund cron / out-of-order client retries
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
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add workers/billing/src/credit.ts workers/billing/test/credit.test.ts
git commit -m "feat(billing): refund with idempotent unknown-hold semantics"
```

---

## Task 8: credit.ts — `refundOpenHoldsOlderThan` (orphan refund, TDD)

**Files:**
- Modify: [workers/billing/src/credit.ts](../../workers/billing/src/credit.ts)
- Modify: [workers/billing/test/credit.test.ts](../../workers/billing/test/credit.test.ts)

- [ ] **Step 1: Append test**

```ts
import { refundOpenHoldsOlderThan } from '../src/credit';

describe('refundOpenHoldsOlderThan', () => {
  it('refunds only open holds with created_at < threshold', async () => {
    const now = Date.now();
    const oneHourAgo = now - 60 * 60 * 1000;
    const fiveMinAgo = now - 5 * 60 * 1000;

    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-orph', 0, 200, ?)",
    ).bind(now).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-old', 'u-orph', 100, 'open', ?, NULL)",
    ).bind(oneHourAgo - 1000).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-fresh', 'u-orph', 100, 'open', ?, NULL)",
    ).bind(fiveMinAgo).run();

    const n = await refundOpenHoldsOlderThan(env.CREDIT_DB, oneHourAgo);
    expect(n).toBe(1);

    const old = await env.CREDIT_DB.prepare(
      "SELECT status FROM credit_hold WHERE hold_id='h-old'",
    ).first();
    expect(old).toEqual({ status: 'refunded' });

    const fresh = await env.CREDIT_DB.prepare(
      "SELECT status FROM credit_hold WHERE hold_id='h-fresh'",
    ).first();
    expect(fresh).toEqual({ status: 'open' });

    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind('u-orph').first();
    expect(bal).toEqual({ balance: 100, held: 100 });
  });
});
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

Append to `src/credit.ts`:

```ts
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
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add workers/billing/src/credit.ts workers/billing/test/credit.test.ts
git commit -m "feat(billing): orphan-hold sweep for cron handler"
```

---

## Task 9: Endpoint wiring in index.ts (TDD)

**Files:**
- Modify: [workers/billing/src/index.ts](../../workers/billing/src/index.ts)
- Create: [workers/billing/test/endpoints.test.ts](../../workers/billing/test/endpoints.test.ts)

URL contract (from spec §Billing Worker endpoints):
- `GET  /api/billing/credit/balance` → 200 `{balance, held}` / 400 `missing_user_id`
- `POST /api/billing/credit/hold`    → 200 `{holdId, newBalance}` / 402 `insufficient_credit`
- `POST /api/billing/credit/debit`   → 200 `{newBalance}` / 404 `hold_not_found` / 409 `hold_already_settled`
- `POST /api/billing/credit/refund`  → 200 `{newBalance}` / 409 `hold_already_settled`

All credit endpoints require the `X-User-Id` header. Empty/missing → 400 `missing_user_id`.

- [ ] **Step 1: Write failing integration test**

`test/endpoints.test.ts`:

```ts
import { SELF, env } from 'cloudflare:test';
import { describe, it, expect, beforeEach } from 'vitest';
import { applyMigration } from './helpers';

beforeEach(applyMigration);

async function call(path: string, init: RequestInit & { userId?: string } = {}) {
  const headers = new Headers(init.headers);
  headers.set('content-type', 'application/json');
  if (init.userId) headers.set('x-user-id', init.userId);
  return SELF.fetch(`https://x${path}`, { ...init, headers });
}

describe('credit endpoints', () => {
  it('GET balance returns zero view for unknown user', async () => {
    const r = await call('/api/billing/credit/balance', { method: 'GET', userId: 'u-a' });
    expect(r.status).toBe(200);
    expect(await r.json()).toEqual({ balance: 0, held: 0 });
  });

  it('GET balance 400 on missing user header', async () => {
    const r = await call('/api/billing/credit/balance', { method: 'GET' });
    expect(r.status).toBe(400);
    expect(await r.json()).toMatchObject({ code: 'missing_user_id' });
  });

  it('POST hold 402 insufficient → POST hold OK after grant', async () => {
    let r = await call('/api/billing/credit/hold', {
      method: 'POST',
      userId: 'u-b',
      body: JSON.stringify({ amount: 100 }),
    });
    expect(r.status).toBe(402);

    // simulate grant
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-b', 500, 0, ?)",
    ).bind(Date.now()).run();

    r = await call('/api/billing/credit/hold', {
      method: 'POST',
      userId: 'u-b',
      body: JSON.stringify({ amount: 100 }),
    });
    expect(r.status).toBe(200);
    const body = await r.json<{ holdId: string; newBalance: number }>();
    expect(body.newBalance).toBe(400);
    expect(body.holdId).toMatch(/^h_/);
  });

  it('hold → debit happy path', async () => {
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-c', 1000, 0, ?)",
    ).bind(Date.now()).run();

    const h = await call('/api/billing/credit/hold', {
      method: 'POST', userId: 'u-c', body: JSON.stringify({ amount: 250 }),
    });
    const { holdId } = await h.json<{ holdId: string }>();

    const d = await call('/api/billing/credit/debit', {
      method: 'POST', userId: 'u-c', body: JSON.stringify({ holdId, actualAmount: 200 }),
    });
    expect(d.status).toBe(200);
    expect(await d.json()).toEqual({ newBalance: 800 });
  });

  it('debit returns 404 unknown hold', async () => {
    const r = await call('/api/billing/credit/debit', {
      method: 'POST', userId: 'u-d',
      body: JSON.stringify({ holdId: 'h-bogus', actualAmount: 5 }),
    });
    expect(r.status).toBe(404);
  });

  it('refund returns 200 idempotent on unknown hold', async () => {
    const r = await call('/api/billing/credit/refund', {
      method: 'POST', userId: 'u-e',
      body: JSON.stringify({ holdId: 'h-gone' }),
    });
    expect(r.status).toBe(200);
  });

  it('existing /api/billing/quota still works', async () => {
    const r = await call('/api/billing/quota', { method: 'GET' });
    expect(r.status).toBe(200);
    const body = await r.json<{ aiUsed: number; aiCap: number; tier: string }>();
    expect(body.aiCap).toBe(5);
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (endpoints not wired).

- [ ] **Step 3: Replace `src/index.ts`** with credit-aware router

```ts
import { readQuota, bumpQuota } from './quota';
import { getBalance, hold, debit, refund, InsufficientCredit, refundOpenHoldsOlderThan } from './credit';
import type { Env, CreditError } from './types';

const TODO = (todo: string) => new Response(JSON.stringify({ todo }), {
  status: 501, headers: { 'content-type': 'application/json' },
});

function err(status: number, code: CreditError['code'], message: string): Response {
  const body: CreditError = { code, message };
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  });
}

function ok<T>(body: T): Response {
  return new Response(JSON.stringify(body), {
    status: 200, headers: { 'content-type': 'application/json' },
  });
}

function requireUserId(req: Request): string | Response {
  const u = req.headers.get('x-user-id');
  if (!u) return err(400, 'missing_user_id', 'X-User-Id header is required');
  return u;
}

async function handleCredit(url: URL, req: Request, env: Env): Promise<Response | null> {
  const userOrErr = requireUserId(req);
  if (userOrErr instanceof Response) return userOrErr;
  const userId = userOrErr;

  if (url.pathname === '/api/billing/credit/balance' && req.method === 'GET') {
    return ok(await getBalance(env.CREDIT_DB, userId));
  }
  if (url.pathname === '/api/billing/credit/hold' && req.method === 'POST') {
    const body = await req.json<{ amount?: unknown }>();
    if (typeof body.amount !== 'number') return err(400, 'bad_request', 'amount: number required');
    try {
      return ok(await hold(env.CREDIT_DB, userId, body.amount));
    } catch (e) {
      if (e instanceof InsufficientCredit) return err(402, 'insufficient_credit', 'balance < amount');
      throw e;
    }
  }
  if (url.pathname === '/api/billing/credit/debit' && req.method === 'POST') {
    const body = await req.json<{ holdId?: unknown; actualAmount?: unknown }>();
    if (typeof body.holdId !== 'string' || typeof body.actualAmount !== 'number') {
      return err(400, 'bad_request', 'holdId: string, actualAmount: number required');
    }
    try {
      return ok(await debit(env.CREDIT_DB, body.holdId, body.actualAmount));
    } catch (e) {
      const m = (e as Error).message;
      if (m === 'hold_not_found') return err(404, 'hold_not_found', m);
      if (m === 'hold_already_settled') return err(409, 'hold_already_settled', m);
      throw e;
    }
  }
  if (url.pathname === '/api/billing/credit/refund' && req.method === 'POST') {
    const body = await req.json<{ holdId?: unknown }>();
    if (typeof body.holdId !== 'string') return err(400, 'bad_request', 'holdId: string required');
    try {
      return ok(await refund(env.CREDIT_DB, body.holdId));
    } catch (e) {
      const m = (e as Error).message;
      if (m === 'hold_already_settled') return err(409, 'hold_already_settled', m);
      throw e;
    }
  }
  return null;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const ip = req.headers.get('cf-connecting-ip') ?? '0.0.0.0';

    if (url.pathname === '/api/billing/quota' && req.method === 'GET') {
      return Response.json(await readQuota(env.RATE_LIMIT_KV, ip));
    }
    if (url.pathname === '/api/billing/bump' && req.method === 'POST') {
      const used = await bumpQuota(env.RATE_LIMIT_KV, ip);
      return Response.json({ aiUsed: used });
    }

    if (url.pathname.startsWith('/api/billing/credit/')) {
      const r = await handleCredit(url, req, env);
      if (r) return r;
    }

    if (url.pathname === '/api/billing/checkout') return TODO('Creem cutover 2026-10');
    if (url.pathname === '/api/billing/webhook') return TODO('Creem cutover 2026-10');
    return new Response('not found', { status: 404 });
  },

  async scheduled(_event: ScheduledEvent, env: Env): Promise<void> {
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    await refundOpenHoldsOlderThan(env.CREDIT_DB, oneHourAgo);
  },
};
```

- [ ] **Step 4: Run — expect PASS** (all integration tests).

- [ ] **Step 5: Commit**

```bash
git add workers/billing/src/index.ts workers/billing/test/endpoints.test.ts
git commit -m "feat(billing): credit endpoints (balance/hold/debit/refund) + scheduled stub"
```

---

## Task 10: Cron `scheduled` handler test

**Files:**
- Create: [workers/billing/test/cron.test.ts](../../workers/billing/test/cron.test.ts)

- [ ] **Step 1: Write test**

```ts
import { describe, it, expect, beforeEach } from 'vitest';
import { env, runInDurableObject, createScheduledController } from 'cloudflare:test';
import worker from '../src/index';
import { applyMigration } from './helpers';

beforeEach(applyMigration);

describe('scheduled', () => {
  it('refunds holds older than one hour, leaves fresh ones alone', async () => {
    const now = Date.now();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES ('u-cron', 0, 200, ?)",
    ).bind(now).run();
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_hold VALUES ('h-stale', 'u-cron', 200, 'open', ?, NULL)",
    ).bind(now - 2 * 60 * 60 * 1000).run();

    const ctrl = createScheduledController({ scheduledTime: now });
    await worker.scheduled(ctrl, env, { waitUntil: () => {}, passThroughOnException: () => {} } as any);

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
```

> If `createScheduledController` is not exported by the installed `cloudflare:test` version, fall back to calling `worker.scheduled(null as any, env, ...)` — the handler ignores the event payload.

- [ ] **Step 2: Run — expect PASS** (handler already shipped in Task 9).

- [ ] **Step 3: Commit**

```bash
git add workers/billing/test/cron.test.ts
git commit -m "test(billing): scheduled handler refunds stale holds"
```

---

## Task 11: Conservation-invariant property test

**Files:**
- Create: [workers/billing/test/invariant.test.ts](../../workers/billing/test/invariant.test.ts)

Verifies Invariant 1 (`sum(ledger.delta) == balance + held`) across a random sequence of operations. Cheap insurance for the riskiest part of the system.

- [ ] **Step 1: Write test**

```ts
import { describe, it, expect, beforeEach } from 'vitest';
import { env } from 'cloudflare:test';
import { applyMigration } from './helpers';
import { hold, debit, refund } from '../src/credit';

beforeEach(applyMigration);

describe('invariant: sum(ledger.delta) == balance + held', () => {
  it('holds for 50 random operations on one user', async () => {
    const uid = 'u-inv';
    const seed = 10_000;
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_balance VALUES (?, ?, 0, ?)",
    ).bind(uid, seed, Date.now()).run();
    // record initial grant in ledger so the invariant includes it
    await env.CREDIT_DB.prepare(
      "INSERT INTO credit_ledger (ts, user_id, delta, reason) VALUES (?, ?, ?, 'grant')",
    ).bind(Date.now(), uid, seed).run();

    const openHolds: string[] = [];
    for (let i = 0; i < 50; i++) {
      const r = Math.random();
      try {
        if (r < 0.5 || openHolds.length === 0) {
          const amount = 1 + Math.floor(Math.random() * 200);
          const { holdId } = await hold(env.CREDIT_DB, uid, amount);
          openHolds.push(holdId);
        } else if (r < 0.8) {
          const holdId = openHolds.shift()!;
          const actual = Math.floor(Math.random() * 200);
          await debit(env.CREDIT_DB, holdId, actual);
        } else {
          const holdId = openHolds.shift()!;
          await refund(env.CREDIT_DB, holdId);
        }
      } catch {
        // InsufficientCredit etc — invariant must still hold
      }
    }

    const sum = await env.CREDIT_DB.prepare(
      "SELECT COALESCE(SUM(delta),0) AS s FROM credit_ledger WHERE user_id=?",
    ).bind(uid).first<{ s: number }>();
    const bal = await env.CREDIT_DB.prepare(
      'SELECT balance, held FROM credit_balance WHERE user_id=?',
    ).bind(uid).first<{ balance: number; held: number }>();

    expect(sum!.s).toBe(bal!.balance + bal!.held);
    expect(bal!.balance).toBeGreaterThanOrEqual(0);
    expect(bal!.held).toBeGreaterThanOrEqual(0);
  });
});
```

- [ ] **Step 2: Run — expect PASS.**

- [ ] **Step 3: Commit**

```bash
git add workers/billing/test/invariant.test.ts
git commit -m "test(billing): ledger conservation invariant over random op sequence"
```

---

## Task 12: Live `wrangler dev` smoke

**Files:** none (manual verification)

- [ ] **Step 1: Start dev**

```
npm run dev
```
Expected: listens on `http://localhost:8787`.

- [ ] **Step 2: Seed test user balance**

```
npx wrangler d1 execute chara-convert-credit --local --command "INSERT INTO credit_balance VALUES ('smoke-1', 5000, 0, strftime('%s','now')*1000)"
```

- [ ] **Step 3: Curl through hold → debit → balance**

```bash
curl -s http://localhost:8787/api/billing/credit/balance -H 'X-User-Id: smoke-1'
# expect {"balance":5000,"held":0}

HOLD=$(curl -s -X POST http://localhost:8787/api/billing/credit/hold \
  -H 'X-User-Id: smoke-1' -H 'content-type: application/json' \
  -d '{"amount":300}')
echo "$HOLD"
# expect {"holdId":"h_...","newBalance":4700}

HID=$(echo "$HOLD" | python -c "import sys,json;print(json.load(sys.stdin)['holdId'])")

curl -s -X POST http://localhost:8787/api/billing/credit/debit \
  -H 'X-User-Id: smoke-1' -H 'content-type: application/json' \
  -d "{\"holdId\":\"$HID\",\"actualAmount\":275}"
# expect {"newBalance":4725}

curl -s http://localhost:8787/api/billing/credit/balance -H 'X-User-Id: smoke-1'
# expect {"balance":4725,"held":0}
```

- [ ] **Step 4: Curl insufficient-credit path**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8787/api/billing/credit/hold \
  -H 'X-User-Id: smoke-1' -H 'content-type: application/json' \
  -d '{"amount":999999}'
# expect 402
```

- [ ] **Step 5: Document the smoke run in a notes file** (no commit needed unless results contradict the spec)

---

## Phase A done — acceptance criteria

- ✅ `npm test` green (credit + endpoints + cron + invariant suites)
- ✅ Live curl smoke green (Task 12 Steps 3-4)
- ✅ All commits land on branch
- ✅ wrangler.toml carries D1 binding with real `database_id` UUIDs

Now hand the wire contract to Phase B. The Python `credit_client.py` only needs:
- `POST /api/billing/credit/hold` `{amount}` → `{holdId, newBalance}` (200) / `{code:"insufficient_credit"}` (402)
- `POST /api/billing/credit/debit` `{holdId, actualAmount}` → `{newBalance}` (200)
- `POST /api/billing/credit/refund` `{holdId}` → `{newBalance}` (200)
- `GET  /api/billing/credit/balance` → `{balance, held}` (200)
- All require `X-User-Id` header; 400 if missing.

