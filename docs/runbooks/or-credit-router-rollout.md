# OR Credit Router — Rollout Runbook

**Owner:** ops (zmuleyu)
**Spec:** [docs/specs/2026-05-29-or-credit-router-design.md](../specs/2026-05-29-or-credit-router-design.md)
**Plans:** [docs/plans/2026-05-29-or-credit-router-plan-{A,B,C}-*.md](../plans/)
**Last verified:** TBD on first production run

## Deploy model (read first)

Unlike the original plan, this repo deploys **single-env** through CI:

- `master` push → `.github/workflows/workers-ci.yml` deploys the billing
  Worker to `chara-convert-billing.zmuleyu.workers.dev` if `CF_API_TOKEN` +
  `CF_ACCOUNT_ID` repo secrets are configured.
- `master` push → `.github/workflows/api-ci.yml` deploys the FastAPI shim to
  `chara-convert-shim.fly.dev` if `FLY_API_TOKEN` repo secret is configured.
- `master` push → Cloudflare Pages auto-builds and deploys `apps/web/`.

There is **no staging environment**. The "staging" gate in the original spec
is replaced with the `LLM_ROUTER_MODE` feature flag on Fly: `legacy` (default)
keeps the pre-existing Anthropic/DeepSeek direct path live; flip to `or` once
the Worker, D1, and BYOK are confirmed healthy. Rollback is the same flag
flipped back — no redeploy.

## Prerequisites checklist

- [ ] PR #8 (`feat/or-credit-router`) merged into `master`; CI deploys green.
- [ ] OpenRouter BYOK configured per [openrouter-byok.md](openrouter-byok.md).
- [ ] `OPENROUTER_API_KEY` ready (from BYOK runbook step 4).
- [ ] **D1 database created** — `wrangler.toml` ships with `database_id =
      "REPLACE_AFTER_CREATE"`. CI deploy will fail until this is fixed.
- [ ] Some way to issue `X-User-Id` to web sessions. The current web client
      writes a random `cc.userId` into localStorage on first visit
      ([apps/web/src/lib/billing/userId.ts](../../apps/web/src/lib/billing/userId.ts)); this is fine for the
      single-operator soft-launch but **must** be replaced with a real auth
      identity before public rollout (see spec §Prerequisites §1).
- [ ] OR dashboard "Activity" view bookmarked for cost monitoring.

## Sequence

### 1. One-time: create D1 + apply migration

```bash
cd workers/billing
npx wrangler login            # first time only
npx wrangler d1 create chara-convert-credit
```

Wrangler prints a `database_id`. Paste it into [workers/billing/wrangler.toml](../../workers/billing/wrangler.toml) replacing
`REPLACE_AFTER_CREATE`. If you don't need a preview env, set
`preview_database_id` to the same value or delete the line.

Apply the migration locally then remotely:

```bash
npx wrangler d1 migrations apply chara-convert-credit --local   # sanity check
npx wrangler d1 migrations apply chara-convert-credit --remote
```

Commit the `wrangler.toml` change on its own commit (`chore(billing): wire
real D1 database_id`). CI will deploy on the next master push.

### 2. Worker deploy + smoke

CI auto-deploys after the wrangler.toml commit lands on master. Watch
[the workers-ci run](https://github.com/zmuleyu/chara-convert/actions/workflows/workers-ci.yml).

Smoke from your laptop:

```bash
curl -s https://chara-convert-billing.zmuleyu.workers.dev/api/billing/credit/balance \
  -H 'X-User-Id: smoke-runbook'
# expect {"balance":0,"held":0}
```

If you get a 500, check `wrangler tail chara-convert-billing` — most likely
the migration didn't apply remotely (step 1).

### 3. API — Fly secrets, mode still legacy

Push secrets to Fly *without* flipping the flag yet:

```bash
fly secrets set --app chara-convert-shim \
  OPENROUTER_API_KEY=<from BYOK runbook> \
  BILLING_WORKER_URL=https://chara-convert-billing.zmuleyu.workers.dev
```

`LLM_ROUTER_MODE` defaults to `legacy` via [apps/api/fly.toml](../../apps/api/fly.toml#L20),
so the existing Anthropic/DeepSeek direct path stays live.

Verify legacy path unchanged:

```bash
curl -N -X POST https://chara-convert-shim.fly.dev/api/ai/enrich \
  -H 'content-type: application/json' \
  -d '{"card":{"name":"x","description":"y"},"field":"personality"}'
# expect SSE stream from the legacy backend
```

### 4. Grant yourself test credits

```bash
USER_ID=$(uuidgen)   # or use your existing cc.userId from devtools
NOW_MS=$(( $(date +%s) * 1000 ))
cd workers/billing
npx wrangler d1 execute chara-convert-credit --remote --command \
  "INSERT INTO credit_balance (user_id,balance,held,updated_at) VALUES ('$USER_ID', 10000, 0, $NOW_MS); \
   INSERT INTO credit_ledger (ts,user_id,delta,reason) VALUES ($NOW_MS, '$USER_ID', 10000, 'grant');"
```

Confirm:

```bash
curl -s https://chara-convert-billing.zmuleyu.workers.dev/api/billing/credit/balance \
  -H "X-User-Id: $USER_ID"
# {"balance":10000,"held":0}
```

### 5. Flip the flag → OR

```bash
fly secrets set --app chara-convert-shim LLM_ROUTER_MODE=or
```

Fly restarts the app to pick up the new secret. ~5–10s downtime per machine
(`min_machines_running = 0` means the next request just cold-starts).

Smoke the full hold → stream → debit lifecycle:

```bash
curl -N -X POST https://chara-convert-shim.fly.dev/api/ai/enrich \
  -H "X-User-Id: $USER_ID" \
  -H 'content-type: application/json' \
  -d '{"card":{"name":"Aerin","description":"mage"},"field":"personality"}'
```

Expect SSE chunks, then verify balance dropped:

```bash
curl -s https://chara-convert-billing.zmuleyu.workers.dev/api/billing/credit/balance \
  -H "X-User-Id: $USER_ID"
# balance < 10000, held == 0   (no orphan hold)
```

### 6. Web smoke

`apps/web` deploys automatically through Cloudflare Pages on master push.
The web client already points at the prod billing URL via `PUBLIC_BILLING_BASE`
in `apps/web/.env` (or its Pages-side build env override).

Open https://studio.aichathub.uk (or the current canonical Pages URL), set
`localStorage.setItem('cc.userId', '$USER_ID')` in devtools, hit any AI
enrich button, watch:

- AiAssistPanel shows "Generate" enabled (balance > MIN_BALANCE_TO_TRY=100).
- Network tab: `GET /api/billing/credit/balance` returns 200 with the right
  `X-User-Id` header.
- After enrich completes, balance ticks down in the UI on next poll/refresh.

### 7. Observation window

Watch for ≥48h before declaring stable:

| Signal | Where | Healthy |
|---|---|---|
| `credit.cost_missing` rate | API logs / Fly metrics | ≤ 1% of OR-mode requests |
| OR fallback hit rate | OR dashboard → Activity | primary serves > 90% (low-class), > 80% (high-class) |
| Orphan-hold count | `SELECT count(*) FROM credit_hold WHERE status='open' AND created_at < strftime('%s','now')*1000 - 3600000` | 0 after each cron tick (every 10 min per `wrangler.toml#L26`) |
| D1 storage growth | Cloudflare D1 dashboard | linear-ish; no surprise step changes |
| User reports | Discord / inbox | no "Failed to fetch" / "insufficient credit" complaints from balance>0 users |

## Rollback

The flag is the rollback lever. To revert to the legacy direct-provider path:

```bash
fly secrets set --app chara-convert-shim LLM_ROUTER_MODE=legacy
```

Effect: instant — next request after Fly restart reads the env. Open holds
remain on the books; the cron (`workers/billing` `[triggers] crons =
["*/10 * * * *"]`) refunds them within ~1h via
[refundOpenHoldsOlderThan](../../workers/billing/src/credit.ts).
The Worker + D1 stay deployed — endpoints just stop receiving hold/debit
calls until the flag flips back to `or`.

If the failure is on the Worker side (Worker erroring, not API erroring), the
fail-open at [apps/web/src/lib/billing/client.ts](../../apps/web/src/lib/billing/client.ts) and
[apps/web/src/islands/AiAssistPanel.tsx](../../apps/web/src/islands/AiAssistPanel.tsx) keeps the UI usable —
the API still calls the Worker but tolerates 5xx, and the web button stops
gating on balance. This is by design (commit `da48d0d`); revert to legacy
mode at your leisure.

## Phase A.1 follow-up — required before public mainnet

The current `hold`/`debit`/`refund` impl in
[workers/billing/src/credit.ts](../../workers/billing/src/credit.ts) has known races on `D1.batch()`
documented in [collab/handoffs/2026-05-29-or-credit-router-phase-A-done.md](../../collab/handoffs/2026-05-29-or-credit-router-phase-A-done.md) §Phase A.1.
Mitigation today: the per-user `CreditDO` (commit `fa5146c`) serializes all
mutations for a given `user_id`, which closes the race in practice for the
single-operator soft-launch. Before opening up to multi-tenant public traffic,
revisit the `'open' → 'settling' → 'debited'/'refunded'` two-phase pattern
described in that handoff.

## Open question — re-enabling subscriptions

[apps/web/src/lib/billing/tiers.ts](../../apps/web/src/lib/billing/tiers.ts) is dormant. If subscription
gating is re-enabled later (e.g. free-tier daily grant), the Worker needs a
new `tier` column on `credit_balance` and the Python router's
`pick_model_class` learns a `tier` parameter. Tracked separately; do NOT
silently couple credit + tier in this rollout.
