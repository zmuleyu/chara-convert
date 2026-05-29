# Phase A Done — OR Credit Router

## TL;DR
T1-T12 complete on `feat/or-credit-router`. 26 vitest tests green, tsc clean, live wrangler smoke green. Phase A adversarial review surfaced 4 critical findings; 2 fixed in scope, 2 deferred to Phase A.1 (require schema/DO work, tracked below). Ready for Phase B (Python `credit_client.py`) per [docs/plans/2026-05-29-or-credit-router-plan-A-worker.md#L1241-L1254] wire contract.

## Branch state
- Project: `D:/projects/aichat_group/chara-convert/`
- Branch: `feat/or-credit-router` off `master @ 181d3e7`
- Commits ahead: 11
- Tip: `4298dbc fix(billing): review-driven hardening (no schema/contract changes)`

## Commit log
```
4298dbc fix(billing): review-driven hardening (no schema/contract changes)  [Phase A review fixes]
5e67877 test(billing): ledger conservation invariant over random op sequence [T11]
d642a18 test(billing): scheduled handler refunds stale holds                  [T10]
c59d394 feat(billing): credit endpoints (balance/hold/debit/refund) + scheduled stub [T9]
b09d316 feat(billing): orphan-hold sweep for cron handler                     [T8]
f495f2e feat(billing): refund with idempotent unknown-hold semantics          [T7]
b5973c2 feat(billing): debit with partial-refund and over-debit cap           [T6]
4fed5b3 feat(billing): atomic credit hold with insufficient-credit guard      [T5]
085170f chore(billing): drop dead vitest.workspace.ts from tsconfig include
d9495d6 fix(billing): test infra consistency for pool-workers
9d69476 feat(billing): D1 balance reader (TDD)                                [T4]
357b71e feat(billing): shared types for credit endpoints                      [T3]
ecb3116 feat(billing): D1 migration for credit ledger schema                  [T2]
0238e2d feat(billing): bind D1 CREDIT_DB and cron trigger                     [T1]
```

## Test snapshot
```
Test Files  5 passed (5)
     Tests  26 passed (26)
  quota.test.ts       3
  credit.test.ts      14
  endpoints.test.ts   7
  cron.test.ts        1
  invariant.test.ts   1
tsc --noEmit  0 errors
```

## Live smoke (T12)
See [workers/billing/test/smoke-notes.md](D:/projects/aichat_group/chara-convert/workers/billing/test/smoke-notes.md). All paths green:
balance / hold / debit / balance / 402-insufficient / 400-missing-user / 200-refund-unknown.

## Spec drift discovered & corrected
The original `migrations/0001_credit_ledger.sql` "Invariant 1" comment claimed
`sum(ledger.delta) == balance + held` over all rows. This is impossible with the
shipped impl because `hold` and `refund` rows record **internal** balance<->held
transfers (non-zero delta, zero net effect on b+h). The correct external-conservation
law restricts to `reason IN ('grant','topup','debit')`. Both the migration comment
and the T11 invariant test were updated to encode this; details in commit `5e67877`.

## Phase A.1 — deferred race-condition tickets (REQUIRED before mainnet)

### A.1-1 [CRITICAL] Hold balance race
**Location:** `workers/billing/src/credit.ts` `hold()` lines ~36-58
**Issue:** `SELECT balance` then `db.batch([UPDATE balance, ...])` is non-serializable on D1. Two concurrent holds for the same user_id can both pass the balance check and double-spend; ending state may violate Invariant 3 (`balance >= 0`).
**Why deferred:** D1 has no `SELECT ... FOR UPDATE`. Correct fixes:
  - (preferred) Per-user DurableObject serializing credit mutations
  - CAS pattern: `UPDATE credit_balance ... WHERE balance >= ?` with `meta.changes` check + compensation for orphaned `credit_hold` row
Both require ~1d work and either a schema change or new binding. Plan author opted to ship Phase A first.
**Mitigation today:** Workloads through the `chara-convert` admin path will not generate concurrent holds for a single user_id. Public mainnet rollout must wait for A.1-1.

### A.1-2 [CRITICAL] Debit/refund hold_id race
**Location:** `workers/billing/src/credit.ts` `debit()`, `refund()`
**Issue:** Same SELECT-then-batch pattern. Two concurrent debits on the same `hold_id` can both pass the `status='open'` check; both `db.batch()` calls commit; balance is double-deducted and ledger gets duplicate `'debit'` rows. Adding `AND status='open'` to the inner UPDATE does not help — D1 batch is atomic-on-error, not atomic-on-zero-changes.
**Correct fix:** Two-phase status (`'open' -> 'settling' -> 'debited'/'refunded'`) so the first-phase UPDATE acts as an atomic claim. Requires schema migration to extend the CHECK constraint, plus extending `refundOpenHoldsOlderThan` to also sweep stuck `'settling'` rows.
**Mitigation today:** Same caveat as A.1-1 — internal usage only until fixed.

### A.1-3 [LOW] refund() unknown-hold returns `{newBalance: 0}`
**Location:** `workers/billing/src/credit.ts` `refund()` early-return for `!h`
**Status:** Intentional per plan (idempotent cleanup for cron / orphan refunds). Comment added in commit `4298dbc`. Will not be changed without a spec update — flagging only because the call-site in `index.ts` exposes this to the public API. Phase B Python client should treat `newBalance` from refund as advisory and re-`getBalance()` if it needs accuracy.

## Wire contract for Phase B (verbatim from plan)
- `POST /api/billing/credit/hold`    `{amount}` -> `{holdId, newBalance}` (200) / `{code:"insufficient_credit"}` (402)
- `POST /api/billing/credit/debit`   `{holdId, actualAmount}` -> `{newBalance}` (200) / 404 hold_not_found / 409 hold_already_settled
- `POST /api/billing/credit/refund`  `{holdId}` -> `{newBalance}` (200) / 409 hold_already_settled
- `GET  /api/billing/credit/balance` -> `{balance, held}` (200)
- All require `X-User-Id` header; 400 `missing_user_id` if absent.

## Repo gotchas refresher
- `wrangler whoami` not authenticated; tests use `--local` D1, `wrangler.toml` carries placeholder UUIDs (`REPLACE_AFTER_CREATE`). Replace before remote deploy.
- `compatibility_flags = ["nodejs_compat"]` already set (required by pool-workers).
- Test runtime pinned to `@cloudflare/vitest-pool-workers@0.5.41` + `@cloudflare/workers-types@~4.20241230.0`.
- `__MIGRATION_SQL__` injected via `vitest.config.ts` `define`. **Must be ASCII-safe** — non-Latin1 chars (e.g. em-dash `—` U+2014) in the SQL file break the miniflare ByteString header that ships the value. Migration comment was rewritten to avoid this in commit `5e67877`.
- Max 1 agent at a time (Win10 CLAUDE.md constraint).

## Next session pickup
1. Read this file.
2. If starting Phase A.1 race fixes: see tickets A.1-1 and A.1-2 above. Begin with a new spec under `docs/specs/2026-05-30-credit-router-phase-A1-races.md`.
3. If starting Phase B (Python): see plan [docs/plans/2026-05-29-or-credit-router-plan-B-python.md](D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-B-python.md). Wire contract above is stable.

## TodoWrite state to restore
```
T1-T12: completed
Phase A adversarial review: completed (2 critical fixed, 2 deferred to A.1 tickets)
Phase A.1 (race fixes): pending [BLOCKS mainnet]
Phase B (Python credit_client): pending
Phase B review: pending
Phase C (rollout): pending
```
