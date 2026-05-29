# A.1 T19 Adversarial Review

Date: 2026-05-29
Reviewer: Claude (adversarial-review)
Focus: DO eviction, D1 partial-failure, cron/live-traffic interleaving, error propagation, blockConcurrencyWhile correctness

## Critical (must-fix before mainnet)

(none)

---

## Major (track as A.1.x sub-ticket)

[M1] **credit-do.ts:62-66 (hold error mapping) — hold() exceptions beyond InsufficientCredit are caught generically, may conflate error types**
- **Issue**: If hold() throws an unexpected error (e.g., from db.batch() due to D1 constraint violation or transient network error), the catch at line 64 catches it and returns 500 with code 'bad_request'. This conflates application errors (invalid input, insufficient credit) with transport/infrastructure errors (D1 unavailable). The error code 'bad_request' is semantically incorrect for a database error.
- **Failure mode**: Client receives 500 with code 'bad_request' when D1 experiences a transient error. This makes client-side error handling harder (clients cannot distinguish transient failures they should retry from permanent failures they should report). Additionally, logs show 'bad_request' which is misleading for ops debugging (D1 issue is not a bad request).
- **Fix**: Distinguish D1 errors from application errors in the response. Return 503 for database errors and 500 for unexpected internal errors:
  ```typescript
  } catch (e) {
    if (e instanceof InsufficientCredit) return err(402, 'insufficient_credit', 'balance < amount');
    const m = (e as Error).message;
    if (m.includes('database') || m.includes('SQLITE')) {
      console.error('CreditDO hold D1 error:', e);
      return err(503, 'service_unavailable', 'database unavailable');
    }
    console.error('CreditDO hold unexpected:', e);
    return err(500, 'internal_error', 'internal error');
  }
  ```
  Apply same pattern to debit (lines 72-80) and refund (lines 82-91) handlers.

[M2] **test/vitest.config.ts:21-22 (Windows test isolation) — singleWorker:true + isolatedStorage:false may hide DO eviction scenarios**
- **Issue**: The config uses `singleWorker: true` and `isolatedStorage: false` to avoid EBUSY errors on Windows file locks. This means all tests run in a single isolate with shared DO storage. DO eviction scenarios (a DO evicts mid-batch and re-instantiates with fresh state) cannot be tested. The race tests (race.test.ts) exercise concurrent requests to the same user_id, but they do not exercise DO eviction+re-instantiation failure modes.
- **Failure mode**: Race tests pass, but production code may have a race if a DO is evicted unexpectedly (e.g., Cloudflare memory pressure). The spec at line 69 says blockConcurrencyWhile handles this correctly, but there's no test that simulates eviction+re-instantiation to verify. The current test suite passes on Windows due to environmental luck (no actual evictions), not by design.
- **Why it matters**: The blockConcurrencyWhile guarantee is load-bearing (per spec line 69: "key insight"). If a test harness-specific config accidentally hides a regression in eviction handling, the code ships broken.
- **Fix** (optional, per spec line 99 T20): Add an optional test flag (e.g., `--simulate-do-eviction`) that clears DO storage between concurrent ops, forcing re-instantiation. Or accept T19 scope limits and track as T20 optional. The code is likely correct (D1 is durable, DO has no state), but verification is incomplete on Windows.

[M3] **index.ts:43 (cron batch size) — 500 hardcoded with no backpressure if DO queue builds up**
- **Issue**: Cron enumerates up to 500 stale holds (line 43) and issues sequential DO fetch() calls (line 47-54). If live traffic is heavy on the same user_id, the DO request queue grows. Cron task does not have a timeout or backpressure mechanism. Under high load (e.g., 500 users each with 1 stale hold + active live traffic), cron can accumulate pending refund calls and run for >1 minute.
- **Failure mode**: Cron scheduled task (10-minute trigger per wrangler.toml) may not complete before the next trigger fires, causing cron-on-cron contention. If cron consistently runs >10 minutes, subsequent cron triggers queue up and the system experiences cascading delays in stale hold cleanup.
- **Why it matters**: Spec line 137 acknowledges this as a known risk ("Cron sweep contention"). Not a bug in the current code, but a deferred tuning point. No blocking issue if actual load is light, but should be monitored.
- **Fix**: Per spec, reduce LIMIT (e.g., 100 instead of 500) or add jitter to spread refund calls. This is optional tuning; recommend monitoring first.

---

## Minor (cleanup, no blocker)

[m1] **credit.ts:69 vs 123-128 (debit/refund asymmetry) — missing hold handling differs but lacks cross-commentary**
- **Issue**: debit() throws 'hold_not_found' when hold is missing (line 69), but refund() returns success with newBalance=0 (line 128). The asymmetry is intentional per spec (debit non-idempotent, refund idempotent), but a reader of debit() will not understand why refund() behaves differently without reading the refund comment.
- **Fix**: Add comment to debit() explaining the asymmetry:
  ```typescript
  // NOTE: debit is NOT idempotent by design. A missing hold is an error.
  // refund() is idempotent for cron sweep and client retries (different use case).
  if (!h) throw new Error('hold_not_found');
  ```

[m2] **index.ts:39-40 (cron comment accuracy) — spec says "handle 404" but code returns 200 for missing holds**
- **Issue**: Comment at line 39 says "404 = hold deleted" but refund() (credit.ts:123-128) returns 200 with newBalance=0 when hold is missing, never 404. Cron code (line 55-59) treats 200 as success, which is correct, but the comment is aspirational and misleading.
- **Fix**: Update the comment to reflect actual behavior:
  ```typescript
  // 200 = refunded or hold already gone (idempotent)
  // 409 = hold_already_settled (live debit won the race, or already settled)
  ```

[m3] **credit-do.ts:93 (unknown op response code) — returns 404 but should be 400**
- **Issue**: Line 93 returns 404 'not found' for an unknown operation. HTTP semantics: 404 means "resource not found", but unknown operation is a malformed request (should be 400 Bad Request). The code behavior is correct, but the status code is wrong.
- **Fix**: Return 400 instead of 404.
  ```typescript
  return err(400, 'bad_request', 'unknown op');
  ```

[m4] **credit-do.ts:40-41 (header check order) — validation order is defensible but worth documenting**
- **Issue**: X-User-Id header is checked (line 40-41) before JSON body is parsed (line 48). If a POST request has a missing header and invalid JSON body, the error message is about the header, not the invalid JSON. The order is defensible (headers before body), but not explicitly documented.
- **Note**: No action required. The current order is correct per HTTP conventions.

---

## Verified-safe (areas examined, no finding)

**1. DO eviction mid-batch** — Spec line 54 and code at credit-do.ts:54-94: The entire critical section is wrapped in `blockConcurrencyWhile`, preventing new fetch() handlers from being dispatched until the callback returns. If the DO is evicted during the callback (e.g., Cloudflare memory pressure), the next request creates a fresh DO instance. D1 is durable and the DO has no persistent state (no `this.state` access). All mutations use `db.batch([...])`, which is atomic in D1. If eviction occurs, the next request sees consistent D1 state. This is safe by design. **Verified safe.**

**2. D1 partial-failure inside DO handler** — Code at credit.ts:53, 111, 143: All mutations use `db.batch([...])`, which is all-or-nothing per D1 semantics. If any statement fails, none execute. Partial state is impossible. If batch fails, an error is thrown, the DO handler catches it, and returns 5xx. The next request retries and sees consistent D1 state. **Verified safe.**

**3. cron + live-traffic interleaving** — Spec line 41-64 and code at index.ts:41-65: Cron queries D1 outside the critical section (index.ts:43-44), then calls refund() via DO for each hold (line 50-54). Between the SELECT and per-row refund(), live traffic can debit or refund the hold. The refund() handler checks hold status: if not 'open', throws 'hold_already_settled' (→ 409). Cron skips 409s and continues (line 57-58). If hold is deleted between SELECT and refund(), refund() returns 200 (idempotent). Cron counts it as success. Both cases are safe — no double-settle, no balance corruption. **Verified safe.**

**4. DO 5xx propagation and Worker retry policy** — Spec line 70 and code at index.ts:26-35: Worker wraps DO fetch() in try/catch. Any error from DO (including internal 5xx) is caught and returns 503 to client. The spec mandates Worker MUST NOT retry on DO 5xx (hold is non-idempotent). The code correctly catches and returns 503 (no retry). Clients see 503 and must decide whether to retry. For `hold`, no retry (non-idempotent). For `debit`/`refund`, client can retry (idempotent). This is correct. **Verified safe.**

**5. blockConcurrencyWhile deadlock corners** — Spec line 13-16 and code at credit-do.ts:54-94: Critical section wraps the entire fetch() handler. Inside the critical section, the only awaits are: req.json() (stream parsing, non-blocking), db.prepare().bind().first/all/run (D1 RPC, non-blocking), db.batch() (D1 RPC, non-blocking). No nested DO.fetch() calls or hibernation triggers. No deadlock risk. **Verified safe.**

**6. race-1 marker removal** — Spec line 92-94 and code at race.test.ts:36-61: Race-1 test was shipped with `it.fails` marker at T13, removed at T15 after blockConcurrencyWhile landed. The test now passes deterministically (15 iterations of 5 concurrent holds). Marker removal is solid. **Verified safe.**

**7. Test infra Windows tuning** — Spec line 101-103 and code at vitest.config.ts:21-28, test/helpers.ts: The singleWorker:true + isolatedStorage:false config avoids EBUSY errors on Windows. applyMigration() (test/helpers.ts:8-17) drops tables before creating them, ensuring each test has clean schema. beforeEach() calls applyMigration() (race.test.ts:23, invariant.test.ts:8). Invariant fuzzer runs 60 ops with 30% bursts (invariant.test.ts:110-119). Test suite is deterministic and passes consistently. No regression on Windows. **Verified safe.**

---

## Summary

**Critical findings**: 0
**Major findings**: 3 (error type conflation in hold/debit/refund, test isolation limitation, cron batch size)
**Minor findings**: 4 (error asymmetry comments, cron comment accuracy, HTTP status codes, header order)
**Verified-safe areas**: 7 (eviction, D1 partial-failure, cron interleaving, 5xx propagation, deadlock, race-1 promotion, Windows test tuning)

**Counts**: Critical=0 | Major=3 | Minor=4 | Suggestion=0

The implementation is fundamentally sound. No concrete bugs that block mainnet. M1 (error type conflation) is the most actionable fix (improves debuggability). M2 and M3 are deferred per spec. Minor issues are polish.
