---
title: Credit Router Phase A.1 — Hold/Debit Race Fixes
date: 2026-05-30
architectModel: opus
status: draft
supersedes: none
preserves-wire-contract: true
predecessor: 2026-05-29-or-credit-router-phase-A-recap.md
---

# Credit Router Phase A.1 — Hold/Debit Race Fixes

## Decision

Adopt **per-user Durable Object** (DO) as the single serialization point for all credit mutations (`hold`, `debit`, `refund`, future `topup`/`grant`). DO instance id is derived from `user_id` (`idFromName(user_id)`). D1 remains the durable store; DO is the lock manager only — it reads/writes D1 inside its single-threaded handler.

The four credit endpoints in `workers/billing/src/index.ts` become thin proxies: parse `X-User-Id`, forward the request body to `env.CREDIT_DO.get(idFromName(userId)).fetch(...)`. No wire-contract change — request/response JSON and status codes are byte-identical to Phase A.

## DO vs CAS+compensation — why DO

| Aspect | DO (chosen) | CAS + 'settling' status |
|---|---|---|
| A.1-1 (hold race) fix | DO method body is the critical section; `balance < amount` check and write are naturally atomic | `UPDATE credit_balance SET balance=balance-? WHERE user_id=? AND balance>=?`, check `meta.changes`, compensate orphan `credit_hold` insert on success-but-partial-fail |
| A.1-2 (hold_id race) fix | Same DO handler covers debit + refund; no two-phase status needed | Schema migration: add `'settling'` to CHECK; cron sweep extended to `status='settling' AND settled_at<threshold`; debit/refund become 2-batch ops |
| Schema impact | Zero (Phase A schema unchanged) | Migration `0002_add_settling_status.sql`; CHECK constraint change is destructive on SQLite (table rebuild) |
| Failure modes | DO unavailable → request 503; DO storage / D1 split-brain on DO eviction mid-batch | Partial CAS success → compensation row leak if Worker crashes between batches; settling-stuck rows need cron timeout tuning |
| Future race surface | Free for any new mutation (topup, grant, refund-bonus) | Each new mutation must re-derive its own CAS pattern |
| Operational | One new binding; standard CF pattern; observable via DO metrics | Stays in pure D1; debug via ledger only |
| Latency overhead | +1 fetch hop inside Worker (~1-3ms intra-CF) | Zero hop; +1 D1 batch per debit/refund |
| Cost | DO requests + duration (cheap at our scale) | None |

Decisive factor: A.1-2 requires schema migration regardless of route, and the CAS path leaves a compensation surface that Phase A's adversarial review already flagged as "hard to test exhaustively". DO collapses both races into one serialization primitive and matches the plan author's stated preference in [phase-A-done.md#L60].

## Scope

**In scope (A.1):**
- New file `workers/billing/src/credit-do.ts`: `class CreditDO extends DurableObject` with `fetch()` dispatching to `hold`/`debit`/`refund`/`balance` handlers.
- Edit `workers/billing/src/index.ts`: replace direct `credit.ts` calls with DO forwarding.
- Edit `workers/billing/wrangler.toml`: add `durable_objects.bindings` + `migrations[].new_sqlite_classes` (DO uses no storage API — D1 is sole persistence — but binding declaration is still required).
- Edit `workers/billing/src/cron.ts` (or wherever `refundOpenHoldsOlderThan` is called from `scheduled`): D1 query `SELECT hold_id, user_id FROM credit_hold WHERE status='open' AND created_at<? LIMIT 500` (must include `user_id` to route to the correct DO instance), then for each row call `env.CREDIT_DO.get(env.CREDIT_DO.idFromName(user_id)).fetch(...refund(holdId))`. cron must continue past 409 `hold_already_settled` (live debit won the race) and 404 (hold deleted out from under the sweep).
- Tests: race-condition vitest in `test/race.test.ts` with three describes. **Empirical calibration (T13):**
  - `concurrent-hold` (A.1-1, 5 concurrent fetches against shared balance): race reliably triggers in miniflare (~30% per iter; 8/40 in measured runs). Shipped marked `it.fails` against current Phase A code — the marker reports green now and will auto-flip RED when DO lands, forcing its removal at T15.
  - `concurrent-debit` (A.1-2, 3 concurrent fetches against shared hold): race does NOT reliably trigger in miniflare even at 40 iterations — the 2-3 op concurrency depth is too shallow for better-sqlite3's single synchronous connection. Shipped as a *forward contract* test (passes on current code by environment accident, passes under DO contractually).
  - `concurrent-debit-refund` (A.1-2 cross-op): same disposition as `concurrent-debit`.
  - The A.1-2 production race remains evidenced by Phase A adversarial review's static analysis. T20 (optional) would add a fake-D1 driver with injectable latency to convert these contract tests into RED-first proofs locally.

**Out of scope:**
- Wire contract changes (Phase B Python client depends on stability).
- Schema migrations (Phase A schema is sufficient under DO model).
- `'settling'` status (avoided by DO).
- Multi-region DO placement strategy (single-region is correct for monetary ledger).
- DO hibernation / alarm-based cron (cron stays on Worker, calls DO per row).

## Architecture changes

```
                                       ┌─ idFromName(user_id) ─┐
POST /credit/{hold,debit,refund,balance} ─► Worker ──► DO instance(user_id) ──► D1
                                                       (serialized critical section)
GET  /credit/balance                  ─► Worker ──► DO instance(user_id) ──► D1 (read-only)

scheduled() cron ──► D1 query stale holds ──► for each: CREDIT_DO.refund(holdId)
```

**Notes:**
- `balance` read also routes through DO so it observes consistent post-batch state (and matches Phase A's external contract that returns `{balance, held}` as one snapshot).
- DO `fetch()` parses an internal JSON envelope `{op, ...args}`; this is a private wire, distinct from the public HTTP API. Schema lives in `credit-do.ts` only.
- `credit.ts` functions stay; they become DO-internal helpers. No call-site outside DO (and cron, which still imports the read-side for sweep enumeration only).
- **Critical-section guarantee** (load-bearing, corrected T15): Cloudflare DOs do NOT serialize concurrent `fetch()` handlers by default — awaiting D1 / outbound fetch releases the input gate and the runtime can dispatch the next in-flight request. We therefore wrap the entire credit handler body in `this.ctx.blockConcurrencyWhile(async () => { ... })` to create a true critical section per DO instance (per user_id). Inside the callback awaits still yield to the event loop, but no NEW fetch handler is dispatched until the callback returns. Race tests in `test/race.test.ts` proved this is the actual requirement: input-gate alone failed race-2 1× per 40 iterations; `blockConcurrencyWhile` brought it to 0× per 40 iterations across multiple full-suite runs.
- **Worker → DO retry policy**: Worker MUST NOT retry on DO 5xx — `hold` is non-idempotent (each successful call mints a new `holdId`) and a Worker-level retry could double-mint. `debit`/`refund` are status-idempotent (re-delivery returns 409 `hold_already_settled` after the first success), so clients (Phase B Python `credit_client.py`) may safely retry these with exponential backoff. The Worker propagates DO errors as-is with a 503 wrapper for transport-level failures.

## Invariants (unchanged from Phase A — re-verified under DO)

1. External conservation: `sum(ledger.delta) where reason IN ('grant','topup','debit') == balance + held` per user.
2. Every `credit_hold` row settles to `'debited'` or `'refunded'`.
3. `balance + held >= 0` always.
4. **(new)** All mutations for `user_id=U` are linearizable as observed from outside (DO single-instance guarantee).

## Test plan (TDD, RED-first)

- **race-1 [RED first]** `concurrent-hold.test.ts`: seed user with `balance=100`, fire 5 concurrent `hold(50)` against the same `user_id` via `SELF.fetch`. Expected: exactly 2 succeed, 3 return 402, final `balance + held == 100`. Current Phase A: will fail (Invariant 3 violation possible).
- **race-2 [RED first]** `concurrent-debit.test.ts`: seed hold, fire 3 concurrent `debit(holdId, actualAmount=X)`. Expected: 1 succeeds, 2 return 409 `hold_already_settled`, exactly one `'debit'` ledger row exists.
- **race-3 [RED first]** `concurrent-debit-refund.test.ts`: fire 1 `debit` + 1 `refund` on the same hold. Expected: one wins (response 200), the other returns 409.
- **regression** all 26 Phase A tests must still pass unchanged (they go through the new HTTP→DO path).
- **cron** existing `cron.test.ts` extended: when a hold goes stale mid-cron-execution and a live debit lands, the live debit serializes first via DO; cron's refund call observes `hold_already_settled` and counts down. No double-settle.
- **invariant** `invariant.test.ts` extended random sequence to inject `Promise.all([...])` bursts (not sequential) — the existing serial fuzzer would have missed both races.

All race tests use vitest `Promise.all` against `SELF.fetch` so the miniflare DO scheduler is exercised.

## Implementation order (T-prefixed, matches Phase A convention)

- T13 — **DONE** — race tests in `test/race.test.ts`; race-1 RED-first via `it.fails`; race-2/3 calibrated as contract tests (later promoted to regular `it` at T15). 29/29 suite green.
- T14 — **DONE** — `CREDIT_DO` binding + `[[migrations]] new_classes=["CreditDO"]` in `wrangler.toml`; `class CreditDO extends DurableObject<Env>` in `src/credit-do.ts`; `CREDIT_DO: DurableObjectNamespace` added to `Env`; `export { CreditDO } from './credit-do'` from `src/index.ts`.
- T15 — **DONE** — `index.ts` `handleCredit` collapsed to `proxyToCreditDO` (thin Worker forwarding via `new Request(internalUrl, req)`); DO body wrapped in `ctx.blockConcurrencyWhile` (key insight — input gates alone insufficient; see "Critical-section guarantee" above); race-1 `it.fails` marker removed; full suite 29/29 green ×5 consecutive runs.
- T16 — **DONE** — `scheduled()` rewritten as `refundStaleHoldsViaDO`: D1 `SELECT hold_id, user_id ...` then per-row `stub.fetch('.../refund')`; tolerates 409 (live race winner) and transport errors. Existing `cron.test.ts` continues to assert the refund outcome; passes unchanged.
- T17 — **DONE** — `invariant.test.ts` second describe `conservation under concurrent bursts (HTTP→CreditDO path)` issues 60 random ops via `SELF.fetch` with 30% chance of 2-5-wide `Promise.all` bursts. Conservation + non-negativity hold under bursts; the serial fuzzer above would have passed even if `blockConcurrencyWhile` were removed (no concurrency), so this is the regression net for DO serialization. 30/30 suite green.
- T18 — **DONE** — Live `wrangler dev --local` smoke (see [test/smoke-notes-a1.md](../../workers/billing/test/smoke-notes-a1.md)): all 7 Phase A T12 single-flight steps unchanged under HTTP→DO; 3 concurrency cases (race-1 5×hold, race-2 3×debit, race-3 debit+refund) observe correct DO serialization live.
- T19 — **DONE** — See [collab/reviews/A1-T19-adversarial.md](../../collab/reviews/A1-T19-adversarial.md). 0 critical, 3 major (all known/deferred), 4 minor. 7 focus areas verified-safe (eviction, D1 partial-failure, cron interleaving, 5xx propagation, deadlock, race-1 promotion, Windows test tuning). No mainnet blockers. Tracked as A.1.x sub-tickets below.
- T20 — (optional) fake-D1 driver with `await sleep()` injection to RED-reproduce the Phase A race in pure unit-test form. Skippable if T19 accepts the existing N-iteration burst as evidence.

### Test infra changes landed alongside T14-T16 (Windows-specific)

`vitest.config.ts` had to switch to `singleWorker: true` + `isolatedStorage: false` + `durableObjectsPersist: false` because vitest-pool-workers' per-test DO storage snapshot/restore triggers EBUSY on Windows file unlink. `test/helpers.ts` applyMigration now drops tables before re-creating them so tests stay deterministic without isolated storage. `test/env.d.ts` declares `CREDIT_DO: DurableObjectNamespace` in the ProvidedEnv augmentation so `cron.test.ts` typechecks.

## Wire-contract guarantee

Phase B's `credit_client.py` ([docs/plans/2026-05-29-or-credit-router-plan-B-python.md]) can be implemented in parallel with A.1. The contract enumerated in [phase-A-done.md#L75-L80] is preserved verbatim:
- All 4 endpoints keep paths, request shapes, response shapes, status codes.
- `X-User-Id` header semantics unchanged.
- New failure mode: 503 on DO unavailable. Phase B client should treat 5xx as retryable with exponential backoff (this is a pure addition, not a contract narrowing).

## Rollout

A.1 is a code-only change (no schema migration, no data backfill). Deploy path:
1. Land branch `feat/credit-do` off current `feat/or-credit-router` tip.
2. Merge to `master` after T19 green.
3. `wrangler deploy` to production replaces the Worker atomically. In-flight requests at deploy boundary may see a single retry; DO routing is unaffected (DO instances persist across Worker code reloads).

No staged rollout needed — DO + D1 schema is forward-compatible with Phase A code, but Phase A code is **not** forward-compatible with concurrent traffic, so a rollback would re-open the races. Treat A.1 as the cut-line for opening public mainnet.

## Acceptance criteria

- [x] T13 race tests in place; suite green stable (29/29 ×5 consecutive runs).
- [x] race-1's `it.fails` marker removed at T15 (assertion now deterministically holds under DO).
- [x] race-2 and race-3 pass under DO routing; the `[200,200,409]` violation observed during pre-blockConcurrencyWhile T15 debug is gone.
- [x] All 26 Phase A tests pass unchanged.
- [x] `tsc --noEmit` clean.
- [x] Live wrangler-dev smoke matches Phase A T12 matrix + the 3 new concurrent-burst cases (T18).
- [x] `smoke-notes-a1.md` captures evidence (T18).
- [ ] Adversarial review (T19) signs off; any new criticals tracked here as A.1.x sub-tickets.
- [x] No diff against Phase A's `types.ts` public-shape (added `CREDIT_DO: DurableObjectNamespace` to internal `Env`; public request/response interfaces unchanged → wire contract preserved).

## Risks / deferred

- **DO storage not used** — we rely on D1 only. If a future requirement adds DO-local state (e.g. an in-memory rate limiter), revisit migration declaration. Tracked here as a note; no action.
- **DO cold-start** on first request per user per region. Acceptable at our latency budget. Will revisit if Phase B p99 measurement shows it dominates.
- **A.1.x-M1** (T19) — DO catch-all maps unexpected throws to `500 'bad_request'`, conflating D1 transient errors with malformed input. Fix: split CreditError code union (add `service_unavailable` and `internal_error`), return 503 for D1 errors and 500 for true internals. Wire-contract addition; coordinate with Phase B `credit_client.py` retry classification.
- **A.1.x-M2** (T19) — Windows vitest tuning (`singleWorker:true`, `isolatedStorage:false`) skips per-test DO snapshot/restore. Eviction+re-instantiation is not exercised in CI on this OS. Spec line 99 already proposed T20 (fake-D1 driver with injectable latency) as the closure; promote that to scheduled work if Phase B p99 measurements flag any eviction-driven anomaly.
- **A.1.x-M3** (T19, supersedes "Cron sweep contention" below) — cron LIMIT=500 + sequential DO fetches has no backpressure or per-run timeout. Acceptable under current load; measure first. If contention is observed, lower LIMIT or jitter the sweep.
- **A.1.x-m2/m3** (T19, polish) — `index.ts:39-40` cron comment says "404 = hold deleted" but `refund()` returns idempotent 200; update wording. `credit-do.ts:93` returns 404 for unknown op; should be 400 per HTTP semantics. Both safe to bundle into next billing-doc/cleanup commit.
