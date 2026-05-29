# OR Credit Router — Phase A
_spec generated: 2026-05-29_

## Decision
Shipped the billing Worker + D1 ledger backing the OR credit flow on
`feat/or-credit-router`: 3 tables (`credit_balance`/`credit_hold`/`credit_ledger`),
helpers `getBalance`/`hold`/`debit`/`refund`/`refundOpenHoldsOlderThan` all
wrapped in `db.batch()` for atomicity, 4 REST endpoints + `*/10 * * * *` cron
sweep for orphan refunds. 26 vitest cases green, tsc clean, live wrangler-dev
smoke green.

## Key trade-offs
- **Atomic via `db.batch()`, not transactions**: D1 has no explicit BEGIN/COMMIT;
  batch is the only atomicity primitive. Accepted that SELECT-then-batch is
  non-serializable across concurrent requests (race tickets A.1-1 / A.1-2).
- **Internal `hold`/`refund` ledger rows kept** even though they over-count for
  conservation: spec-grade audit trail beats algebraic purity. Test + migration
  comment rewritten to encode the actual external-conservation invariant
  `sum(delta where reason in 'grant','topup','debit') == balance + held`.
- **`refund` unknown-hold returns `{newBalance:0}`** (no-op): intentional per
  plan — avoids forcing the cron sweep into a special-case error path. Now
  commented as advisory; Phase B Python client must re-`getBalance` if accurate.
- **Hold ID stays `Math.random` base36** (reviewer flagged crypto): handoff
  pinned `^h_[0-9a-z]+$` regex; Cloudflare Workers' Math.random is V8-isolate
  CSPRNG-backed so the weakness is theoretical here.
- **Two CRITICAL race fixes deferred** to Phase A.1: per-user DurableObject or
  schema-migration to a 'settling' intermediate status. Out-of-scope for branch.

## Implementation notes
- `__MIGRATION_SQL__` shipped via miniflare ByteString header — **SQL files
  must be ASCII**; em-dash `—` (U+2014) breaks the test runner (caught when
  reviewer-driven comment update silently broke all 4 test files).
- `scheduled` handler signature must match `(ctrl, env, ctx)` 3-arg form
  for the cron test to call `worker.scheduled!(ctrl, env, ctx)` cleanly.
- `wrangler dev --local` and `wrangler d1 execute --local` share the same
  miniflare DB file but only after dev has started — seeding before `dev` came
  up did not persist (re-seed after dev is live).

## Commits
- 0238e2d feat(billing): bind D1 CREDIT_DB and cron trigger (T1)
- ecb3116 feat(billing): D1 migration for credit ledger schema (T2)
- 357b71e feat(billing): shared types for credit endpoints (T3)
- 9d69476 feat(billing): D1 balance reader (TDD) (T4)
- 4fed5b3 feat(billing): atomic credit hold with insufficient-credit guard (T5)
- b5973c2 feat(billing): debit with partial-refund and over-debit cap (T6)
- f495f2e feat(billing): refund with idempotent unknown-hold semantics (T7)
- b09d316 feat(billing): orphan-hold sweep for cron handler (T8)
- c59d394 feat(billing): credit endpoints + scheduled stub (T9)
- d642a18 test(billing): scheduled handler refunds stale holds (T10)
- 5e67877 test(billing): ledger conservation invariant over random op sequence (T11)
- 4298dbc fix(billing): review-driven hardening (no schema/contract changes)
- 8ccc344 docs(billing): T12 smoke notes + Phase A close handoff
