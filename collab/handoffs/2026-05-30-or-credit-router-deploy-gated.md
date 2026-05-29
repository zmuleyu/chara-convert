---
type: handoff
project: chara-convert
branch: feat/or-credit-router
last_commit: 3e80c1d
status: code-complete-pending-deploy
phase: deploy-gated
---

# OR Credit Router — Code-Complete, Deploy-Gated

## TL;DR

All code & docs for the OR credit router (Phases A + B + C, plus deferred A.1
mitigations via CreditDO) are merged on `feat/or-credit-router` and PR #8 is
open against master. The remaining work cannot be done by Claude — it needs
your CF/Fly credentials at a real terminal. This handoff captures the exact
sequence so you can finish in one sitting.

## Branch state @ 3e80c1d

- 31 commits ahead of `master @ 181d3e7`
- PR: https://github.com/zmuleyu/chara-convert/pull/8
- CI poll: in-session cron `7fa7a67b` checks `gh pr checks 8` every 5 min;
  pings on green or red
- Tracked working tree: clean (everything committed)

## What Claude finished this session

1. **`6f1070f`** — `fix(api): allow X-User-Id + Pages preview origins on CORS`
   (counterpart to worker-side `d0e30c7`)
2. **`3e80c1d`** — `docs(runbooks): OR BYOK setup + credit-router rollout sequence`
   - [docs/runbooks/openrouter-byok.md](../../docs/runbooks/openrouter-byok.md)
   - [docs/runbooks/or-credit-router-rollout.md](../../docs/runbooks/or-credit-router-rollout.md)

Plan-C Tasks 3 + 4 marked complete. Tasks 6 + prod deploy left for you.

## What needs your credentials (cannot be Claude-executed)

These all live in [docs/runbooks/or-credit-router-rollout.md](../../docs/runbooks/or-credit-router-rollout.md);
this is the condensed checklist.

### Block 1 — D1 creation (one-time)

```bash
cd D:/projects/aichat_group/chara-convert/workers/billing
npx wrangler login                          # if not already
npx wrangler d1 create chara-convert-credit
```

Wrangler prints a UUID. Paste it into [workers/billing/wrangler.toml](../../workers/billing/wrangler.toml#L13)
replacing `database_id = "REPLACE_AFTER_CREATE"`. Drop the
`preview_database_id` line or use the same UUID.

```bash
npx wrangler d1 migrations apply chara-convert-credit --local   # sanity
npx wrangler d1 migrations apply chara-convert-credit --remote
git add wrangler.toml
git commit -m "chore(billing): wire real D1 database_id"
git push
```

### Block 2 — GitHub repo secrets

Confirm both are set at https://github.com/zmuleyu/chara-convert/settings/secrets/actions:

| Secret | Used by | Where to get it |
|---|---|---|
| `CF_API_TOKEN` | `.github/workflows/workers-ci.yml` deploy-billing | CF dashboard → My Profile → API Tokens, "Edit Cloudflare Workers" template |
| `CF_ACCOUNT_ID` | same | CF dashboard, right sidebar |
| `FLY_API_TOKEN` | `.github/workflows/api-ci.yml` deploy-fly | `fly tokens create deploy` |

Without these CI skips the deploy jobs (no error, just a notice). Verify by
checking the Actions tab after the next master push.

### Block 3 — Merge PR #8

Once CI is green on PR #8 (in-session cron `7fa7a67b` will ping):

```bash
cd D:/projects/aichat_group/chara-convert
gh pr merge 8 --rebase --admin
```

Workers + Pages + Fly all auto-deploy on master push.

### Block 4 — Fly secrets, flag still `legacy`

```bash
fly secrets set --app chara-convert-shim \
  OPENROUTER_API_KEY=<from BYOK runbook step 4> \
  BILLING_WORKER_URL=https://chara-convert-billing.zmuleyu.workers.dev
```

`LLM_ROUTER_MODE=legacy` is already the default in [apps/api/fly.toml#L20](../../apps/api/fly.toml#L20),
so this push is non-disruptive.

### Block 5 — OR BYOK

Follow [docs/runbooks/openrouter-byok.md](../../docs/runbooks/openrouter-byok.md) end-to-end. Output is the
`OPENROUTER_API_KEY` you set in Block 4.

### Block 6 — Grant yourself credits + smoke

```bash
USER_ID=$(uuidgen)   # or pull your existing cc.userId from devtools localStorage
NOW_MS=$(( $(date +%s) * 1000 ))
cd workers/billing
npx wrangler d1 execute chara-convert-credit --remote --command \
  "INSERT INTO credit_balance (user_id,balance,held,updated_at) VALUES ('$USER_ID', 10000, 0, $NOW_MS); \
   INSERT INTO credit_ledger (ts,user_id,delta,reason) VALUES ($NOW_MS, '$USER_ID', 10000, 'grant');"

curl -s https://chara-convert-billing.zmuleyu.workers.dev/api/billing/credit/balance \
  -H "X-User-Id: $USER_ID"
# expect {"balance":10000,"held":0}
```

### Block 7 — Flip the flag

```bash
fly secrets set --app chara-convert-shim LLM_ROUTER_MODE=or
```

Smoke the full hold→stream→debit lifecycle — runbook §5/§6 has the exact curl.

### Block 8 — Observation window

Watch the four signals in [or-credit-router-rollout.md §7](../../docs/runbooks/or-credit-router-rollout.md):
`credit.cost_missing` rate, OR primary-vs-fallback ratio, orphan-hold count,
D1 storage growth. ≥48h before declaring stable.

## Rollback

One command, instant:

```bash
fly secrets set --app chara-convert-shim LLM_ROUTER_MODE=legacy
```

Open holds auto-refund within ~1h via the `*/10 * * * *` cron. Worker + D1
stay deployed (they just stop receiving traffic until the flag flips back).

## Known caveats (already documented elsewhere)

- **Phase A.1 races** — `hold`/`debit`/`refund` on `D1.batch()` have known
  TOCTOU windows for multi-tenant traffic. The per-user `CreditDO` (commit
  `fa5146c`) serializes mutations enough for single-operator soft-launch but
  the two-phase status pattern needs to land before opening to public traffic.
  Detail: [collab/handoffs/2026-05-29-or-credit-router-phase-A-done.md §Phase A.1](2026-05-29-or-credit-router-phase-A-done.md).
- **Auth identity** — web client writes random `cc.userId` to localStorage
  ([apps/web/src/lib/billing/userId.ts](../../apps/web/src/lib/billing/userId.ts)). Fine for soft-launch; **must**
  be replaced with real auth before public rollout (spec §Prerequisites §1).
- **`tiers.ts` dormant** — kept for future re-enable of subscription gating
  alongside credits. Not coupled in this rollout by design.

## Stale handoffs to ignore

- [2026-05-29-or-credit-router-T5-pickup.md](2026-05-29-or-credit-router-T5-pickup.md)
  — captured at T5; branch has since advanced through T19 + B + C.
- [2026-05-29-or-credit-router-pickup.md](2026-05-29-or-credit-router-pickup.md)
  — pre-implementation; all phases now done.
- [2026-05-29-or-credit-router-phase-A-done.md](2026-05-29-or-credit-router-phase-A-done.md)
  — Phase A snapshot; still useful for the A.1 race ticket details.

## Pickup invocation (next session)

```
继续 @D:/projects/aichat_group/chara-convert/collab/handoffs/2026-05-30-or-credit-router-deploy-gated.md
```
