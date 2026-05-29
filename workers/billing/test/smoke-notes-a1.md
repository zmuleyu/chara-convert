# T18 Smoke — Phase A.1 — 2026-05-29 19:00 local

Wrangler dev (3.114.17) on `:8787`, `--local` miniflare D1 + DurableObject (CreditDO).
Schema reused from Phase A T12 D1; fresh smoke users seeded via `wrangler d1 execute --local`.

Compat-date warning: requested `2026-05-28`, runtime fell back to `2025-07-18` (installed wrangler 3.114.17). No behavioral impact for the surfaces under test.

## Phase A regression matrix (single-flight)

| step | request | response | expected |
|------|---------|----------|----------|
| 1 | `GET /api/billing/credit/balance` (`X-User-Id: smoke-a1-1`) | `{balance:5000, held:0}` | ok |
| 2 | `POST /api/billing/credit/hold` `{amount:300}` | `{holdId:"h_dskuhds4mpqt76m5", newBalance:4700}` | ok, regex `^h_[0-9a-z]+$` |
| 3 | `POST /api/billing/credit/debit` `{holdId, actualAmount:275}` | `{newBalance:4725}` | ok, 5000-300+25 |
| 4 | `GET /api/billing/credit/balance` | `{balance:4725, held:0}` | ok |
| 5 | `POST /api/billing/credit/hold` `{amount:9999999}` | `402 {code:"insufficient_credit"}` | ok |
| 6 | `GET /api/billing/credit/balance` (no `X-User-Id`) | `400 {code:"missing_user_id"}` | ok |
| 7 | `POST /api/billing/credit/refund` `{holdId:"h-bogus"}` | `200 {newBalance:0}` | ok (documented no-op) |

## A.1 concurrent-burst matrix (DO serialization)

All bursts fired via shell `&` with `wait`. Status-code histograms below.

### race-1 — 5 × concurrent `hold(50)` on `smoke-a1-r1` (`balance=100, held=0`)

```
2 × 200
3 × 402
final: {balance:0, held:100}
```

Acceptance: exactly 2 holds succeed (≤ balance); 3 reject with `insufficient_credit`; `balance + held == 100` (Invariant 3 holds). ✓

### race-2 — 3 × concurrent `debit(holdId=h-smoke-a1-r2, actualAmount=200)`

Seed: `smoke-a1-r2` (`balance=700, held=300`), one open hold of 300.

```
1 × 200  body {newBalance:800}
2 × 409  body {code:"hold_already_settled"}
```

Acceptance: exactly one debit settles; the other two observe the settled state and reject. ✓

### race-3 — `debit + refund` concurrent on `h-smoke-a1-r3`

Seed: `smoke-a1-r3` (`balance=600, held=400`), one open hold of 400.

```
debit  : 200 {newBalance:600}
refund : 409 {code:"hold_already_settled"}
```

Acceptance: exactly one settles; the loser observes terminal status. ✓

## Notes

- DO 5xx propagation not exercised here — covered by `cron.test.ts` and unit-level error mapping. Adversarial review (T19) will close that surface.
- Cron sweep not auto-triggered (`Miniflare 3 does not currently trigger scheduled Workers automatically. Use --test-scheduled`). Verified in-process via `cron.test.ts`.
- Wrangler version bump (3 → 4) deferred; current 3.114.17 covers DO + D1 surface used by A.1.

## Result

Phase A.1 T18 acceptance criteria met: Phase A regression matrix unchanged under the new HTTP→DO path; three concurrency cases observe DO serialization invariants live.
