# T12 Smoke — 2026-05-29 17:50 local

Wrangler dev (3.114.17) on `:8787`, `--local` miniflare D1 at
`.wrangler/state/v3/d1/miniflare-D1DatabaseObject/385be5e98b29fb32e0b3c7e0911b608dcd0de37edac1e7397becf8bad6c084d2.sqlite`.

Schema applied via `wrangler d1 migrations apply chara-convert-credit --local`.

## Flow

| step | request | response | expected |
|------|---------|----------|----------|
| seed | `INSERT INTO credit_balance VALUES ('smoke-1', 5000, 0, now)` via `wrangler d1 execute` | `success: true` | ok |
| 1 | `GET  /api/billing/credit/balance` `X-User-Id: smoke-1` | `{balance:5000, held:0}` | ok |
| 2 | `POST /api/billing/credit/hold` `{amount:300}` | `{holdId:"h_tdx2cbnumpqqz87r", newBalance:4700}` | ok, regex `^h_[0-9a-z]+$` |
| 3 | `POST /api/billing/credit/debit` `{holdId, actualAmount:275}` | `{newBalance:4725}` | ok, 5000-300+25 |
| 4 | `GET  /api/billing/credit/balance` | `{balance:4725, held:0}` | ok |
| 5 | `POST /api/billing/credit/hold` `{amount:9999999}` | `402` | ok (insufficient) |
| 6 | `GET  /api/billing/credit/balance` no `X-User-Id` | `400` | ok (missing_user_id) |
| 7 | `POST /api/billing/credit/refund` `{holdId:"h-bogus"}` | `200 {newBalance:0}` | ok (per documented no-op) |

## Notes

- First seed insert appeared to not persist before `wrangler dev` started; re-running it after dev was up fixed it. Cause unclear; possible that miniflare swapped the on-disk handle on startup.
- `wrangler dev` warns "Miniflare 3 does not currently trigger scheduled Workers automatically. Use `--test-scheduled`". The cron handler is covered by the in-process `cron.test.ts` (used `createScheduledController` + `worker.scheduled`), so this warning is non-blocking.

## Result

Phase A T12 acceptance criteria met: live curl smoke matches spec for all paths exercised.
