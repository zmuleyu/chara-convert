# Phase C — Web Client Switch + Production Rollout

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the web client's `useBilling` hook with credit-balance polling, write the BYOK runbook, deploy + flip the feature flag in staging then prod.

**Architecture:** A single React hook change (`useBilling` → `{balance, held}` instead of `{tier, aiUsed, aiCap}`), the existing `tiers.ts` file kept dormant for the post-Creem subscription re-enable, a CF Worker deploy, two runbook docs, and a controlled staging→prod feature-flag flip.

**Tech Stack:** Astro + React (web), Cloudflare Pages, vitest + @testing-library/react, wrangler CLI.

**Dependencies on Phase A + B:** A's Worker must be deployed (real D1, real `database_id`), B's API must ship to Fly with `LLM_ROUTER_MODE` env var support. C runs after both.

**Working directory:**
- Web tasks: `D:/projects/aichat_group/chara-convert/apps/web/`
- Worker deploy: `D:/projects/aichat_group/chara-convert/workers/billing/`
- API deploy: `D:/projects/aichat_group/chara-convert/apps/api/`
- Runbooks: `D:/projects/aichat_group/chara-convert/docs/runbooks/`

---

## File structure (this phase)

| File | Status | Responsibility |
|---|---|---|
| `apps/web/src/lib/billing/client.ts` | rewrite | poll `/api/billing/credit/balance`, expose `{balance, held, loaded}` |
| `apps/web/src/lib/billing/__tests__/client.test.ts` | rewrite | mock the new endpoint shape |
| `apps/web/src/lib/billing/tiers.ts` | annotate | keep file, add `// DORMANT: pure-credit pivot 2026-05-29` header |
| `docs/runbooks/openrouter-byok.md` | create | dashboard BYOK config + key rotation |
| `docs/runbooks/or-credit-router-rollout.md` | create | staging→prod sequence with rollback |
| `apps/api/fly.toml` | modify | add `LLM_ROUTER_MODE` + `BILLING_WORKER_URL` + `OPENROUTER_API_KEY` secret refs |
| `workers/billing/wrangler.toml` | already done in A | reference only |

---

## Task 1: Web hook rewrite (TDD)

**Files:**
- Modify: [apps/web/src/lib/billing/client.ts](../../apps/web/src/lib/billing/client.ts)
- Modify: [apps/web/src/lib/billing/__tests__/client.test.ts](../../apps/web/src/lib/billing/__tests__/client.test.ts)

New shape:

```ts
interface CreditState {
  balance: number; // credits, integer
  held: number;
  loaded: boolean;
  userId: string | null;
}
```

`loaded=false` until first response, so the UI can show a spinner instead of "0 credit" (which would imply a 402).

- [ ] **Step 1: Rewrite the test file**

```ts
// apps/web/src/lib/billing/__tests__/client.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useBilling } from '../client';

describe('useBilling (credit)', () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it('fetches /api/billing/credit/balance with X-User-Id when present', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ balance: 4500, held: 100 }),
    });
    vi.stubGlobal('fetch', mockFetch);
    vi.stubGlobal('localStorage', { getItem: () => 'u-test', setItem: () => {} } as any);

    const { result } = renderHook(() => useBilling());
    expect(result.current).toMatchObject({ balance: 0, held: 0, loaded: false });

    await waitFor(() => {
      expect(result.current).toMatchObject({ balance: 4500, held: 100, loaded: true });
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/billing/credit/balance'),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ 'X-User-Id': 'u-test' }),
      }),
    );
  });

  it('does not fetch when no userId in storage; reports loaded=true with zero', async () => {
    const mockFetch = vi.fn();
    vi.stubGlobal('fetch', mockFetch);
    vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => {} } as any);

    const { result } = renderHook(() => useBilling());
    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current).toMatchObject({ balance: 0, held: 0, userId: null });
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('falls back to {balance:0, held:0, loaded:true} on fetch failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')));
    vi.stubGlobal('localStorage', { getItem: () => 'u-test', setItem: () => {} } as any);

    const { result } = renderHook(() => useBilling());
    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current.balance).toBe(0);
  });
});
```

- [ ] **Step 2: Run — expect FAIL.**

```
cd apps/web && npx vitest run src/lib/billing/__tests__/client.test.ts
```

- [ ] **Step 3: Rewrite `client.ts`**

```ts
// apps/web/src/lib/billing/client.ts
import { useEffect, useState } from 'react';

export interface CreditState {
  balance: number;
  held: number;
  loaded: boolean;
  userId: string | null;
}

const INITIAL: CreditState = { balance: 0, held: 0, loaded: false, userId: null };

function readUserId(): string | null {
  try {
    return (globalThis.localStorage?.getItem('cc.userId') as string | null) ?? null;
  } catch {
    return null;
  }
}

export function useBilling(): CreditState {
  const [state, setState] = useState<CreditState>(INITIAL);

  useEffect(() => {
    const userId = readUserId();
    if (!userId) {
      setState({ ...INITIAL, loaded: true });
      return;
    }

    const BASE =
      (import.meta.env.PUBLIC_BILLING_BASE as string | undefined) ??
      'http://localhost:8787';

    fetch(`${BASE}/api/billing/credit/balance`, {
      method: 'GET',
      headers: { 'X-User-Id': userId },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.json() as Promise<{ balance: number; held: number }>;
      })
      .then((data) => {
        setState({ balance: data.balance, held: data.held, loaded: true, userId });
      })
      .catch(() => {
        setState({ balance: 0, held: 0, loaded: true, userId });
      });
  }, []);

  return state;
}
```

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/billing/client.ts apps/web/src/lib/billing/__tests__/client.test.ts
git commit -m "feat(web): useBilling polls /credit/balance with X-User-Id; loaded flag"
```

---

## Task 2: Annotate `tiers.ts` as dormant

**Files:**
- Modify: [apps/web/src/lib/billing/tiers.ts](../../apps/web/src/lib/billing/tiers.ts)

Keep the file as-is so a future Creem cutover can re-enable subscriptions without rewriting. Add a header comment that explains why it's not imported.

- [ ] **Step 1: Prepend banner**

```ts
// DORMANT 2026-05-29: pure-credit pivot drops subscription tiers as a routing
// input. This file is intentionally retained — see
// docs/specs/2026-05-29-or-credit-router-design.md §Key trade-offs and
// docs/runbooks/or-credit-router-rollout.md for the conditions under which we'd
// re-import these constants.
//
export type TierId = 'free' | 'creator' | 'studio';
// ... (rest of file unchanged)
```

- [ ] **Step 2: Verify nothing imports `tiers.ts`** (after Task 1, the old import is gone)

```
cd apps/web && grep -rn "from.*billing/tiers" src/
```
Expected: no matches (or only inside `__tests__` legacy snapshots — fine to leave).

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/lib/billing/tiers.ts
git commit -m "docs(web): mark billing/tiers.ts dormant pending subscription re-enable"
```

---

## Task 3: OR BYOK runbook

**Files:**
- Create: [docs/runbooks/openrouter-byok.md](../runbooks/openrouter-byok.md)

> Spec §Prerequisites §2: "Strongly recommended day 1 to capture direct-provider rates; system functions without BYOK (OR billed at retail)."

- [ ] **Step 1: Write runbook**

```markdown
# OpenRouter BYOK Configuration

**Owner:** ops
**Last verified:** TBD on first run
**Related:** docs/specs/2026-05-29-or-credit-router-design.md

## Why

OpenRouter routes to the cheapest available provider per request. With BYOK
(Bring Your Own Key) for DeepSeek + Anthropic configured in the OR dashboard,
OR forwards traffic through *our* provider keys and bills only the 5.5%
routing fee. Without BYOK, OR bills at retail rates (~30–60% markup).

## Prerequisites

- OpenRouter account at https://openrouter.ai
- DeepSeek API key (https://platform.deepseek.com)
- Anthropic API key (separate from chara-convert's existing Fly secret)

## Steps

1. Log into OpenRouter dashboard → Integrations.
2. For each provider (DeepSeek, Anthropic):
   - Click "Add Integration" → select provider.
   - Paste the API key.
   - Save. OR will verify with a low-cost test call.
3. Settings → Default Provider Order: leave at "Lowest price" (matches the
   `provider.sort=price` we send per-request).
4. Generate an OpenRouter API key (Settings → Keys). Note it — used as
   `OPENROUTER_API_KEY` in Fly secrets.
5. Verify BYOK is active for a sample request:
   ```
   curl https://openrouter.ai/api/v1/chat/completions \
     -H "Authorization: Bearer $OR_KEY" \
     -H "content-type: application/json" \
     -d '{"model":"deepseek/deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":5,"usage":{"include":true}}'
   ```
   Check the `usage.cost` field — should reflect direct DeepSeek pricing
   ($0.14/M input) plus 5.5% OR fee, not retail.

## Key rotation

- Provider keys: rotate in provider dashboard, then update integration entry in OR.
- OR key: generate new, deploy to Fly via `fly secrets set OPENROUTER_API_KEY=...`,
  then revoke old in OR Settings → Keys.

## Failure mode

If BYOK is misconfigured (e.g. revoked provider key), OR falls back to its own
retail keys and bills accordingly. Detect via the monthly
`scripts/pricing_drift_check.py` and OR dashboard "Activity" page (cost-per-call
spike). No traffic interruption.
```

- [ ] **Step 2: Commit**

```bash
git add docs/runbooks/openrouter-byok.md
git commit -m "docs(runbooks): OR BYOK setup + key rotation procedure"
```

---

## Task 4: Rollout runbook

**Files:**
- Create: [docs/runbooks/or-credit-router-rollout.md](../runbooks/or-credit-router-rollout.md)

Encodes spec §Migration & rollout as a step-by-step ops doc. Sequence matters — out-of-order = brief production breakage.

- [ ] **Step 1: Write runbook**

```markdown
# OR Credit Router — Rollout Runbook

**Owner:** ops
**Spec:** docs/specs/2026-05-29-or-credit-router-design.md
**Plans:** docs/plans/2026-05-29-or-credit-router-plan-{A,B,C}.md

## Prerequisites checklist

- [ ] Phase A test suite green; Worker deploys cleanly to staging.
- [ ] Phase B test suite green; API deploys cleanly to Fly staging.
- [ ] Phase C web hook tests green.
- [ ] OR BYOK runbook completed (docs/runbooks/openrouter-byok.md).
- [ ] User-auth system issues `X-User-Id` for paying users. (Blocking — see spec §Prerequisites §1.)
- [ ] Monitoring dashboard ready: `credit.cost_missing` metric + OR fallback hit rate.

## Sequence

### 1. Worker + D1 — staging

```
cd workers/billing
npx wrangler d1 migrations apply chara-convert-credit --env staging
npx wrangler deploy --env staging
```

Smoke (from your laptop):

```
curl -s https://<staging-worker>.workers.dev/api/billing/credit/balance \
  -H 'X-User-Id: smoke-runbook'
# expect {"balance":0,"held":0}
```

### 2. API — staging with flag OFF

Add Fly secrets (staging):

```
fly secrets set --app chara-convert-api-staging \
  OPENROUTER_API_KEY=<from BYOK runbook> \
  BILLING_WORKER_URL=https://<staging-worker>.workers.dev \
  LLM_ROUTER_MODE=legacy
```

Deploy:

```
fly deploy --app chara-convert-api-staging
```

Verify legacy path unchanged:

```
curl -X POST https://<staging-api>/api/ai/enrich \
  -H 'content-type: application/json' \
  -d '{"card":{"name":"x","description":"y"},"field":"personality"}'
# expect SSE stream from legacy backend (anthropic or mock per existing keys)
```

### 3. Grant test credits

```
npx wrangler d1 execute chara-convert-credit --env staging --command \
  "INSERT INTO credit_balance VALUES ('staging-tester-1', 10000, 0, strftime('%s','now')*1000); \
   INSERT INTO credit_ledger (ts,user_id,delta,reason) VALUES (strftime('%s','now')*1000,'staging-tester-1',10000,'grant');"
```

### 4. Flip API flag → OR (staging)

```
fly secrets set --app chara-convert-api-staging LLM_ROUTER_MODE=or
```

Smoke the full hold→stream→debit:

```
curl -N -X POST https://<staging-api>/api/ai/enrich \
  -H 'X-User-Id: staging-tester-1' \
  -H 'content-type: application/json' \
  -d '{"card":{"name":"Aerin","description":"mage"},"field":"personality"}'
```

Expected: SSE chunks, then verify balance dropped:

```
curl -s https://<staging-worker>.workers.dev/api/billing/credit/balance \
  -H 'X-User-Id: staging-tester-1'
# balance < 10000, held == 0
```

### 5. Web — staging

```
cd apps/web
# PUBLIC_BILLING_BASE already in .env.staging — verify it points at staging worker
npm run build
npm run deploy:staging   # or wrangler pages deploy
```

Open the staging frontend, set `localStorage.setItem('cc.userId', 'staging-tester-1')` in devtools, hit AI enrich, watch balance tick down in the UI.

### 6. One-week observation (staging)

Watch:
- `credit.cost_missing` metric — should be ≤ 1% of OR-mode requests.
- OR fallback hit rate — primary should serve > 90% (low-class) / > 80% (high-class).
- Orphan-hold count (`SELECT count(*) FROM credit_hold WHERE status='open' AND created_at < strftime('%s','now')*1000 - 3600000`) — should be 0 after each cron tick (every 10 min).
- D1 storage growth on `credit_ledger` — sanity check vs traffic.

### 7. Prod cutover

Repeat steps 1, 2, 4, 5 against the prod app/worker:

```
fly secrets set --app chara-convert-api <secrets...>
npx wrangler d1 migrations apply chara-convert-credit --env production
npx wrangler deploy --env production
fly secrets set --app chara-convert-api LLM_ROUTER_MODE=or
```

Web client deploys via existing Pages pipeline.

## Rollback

The flag is the rollback lever. To revert any environment:

```
fly secrets set --app <api-app> LLM_ROUTER_MODE=legacy
```

Effect: instant — the next request reads the env at module level. Open holds
remain on the books; the orphan-hold cron refunds them within ~1h.
Worker + D1 stay deployed (no rollback needed — endpoints just stop receiving
hold/debit calls until the flag flips again).

## Open question — re-enabling subscriptions

`apps/web/src/lib/billing/tiers.ts` is dormant. If we re-enable
subscription gating later (e.g. for free-tier daily grant), the Worker needs
a new `tier` column on `credit_balance` and `pick_model_class` learns a
`tier` parameter. Tracked separately; do NOT silently couple credit + tier in
this rollout.
```

- [ ] **Step 2: Commit**

```bash
git add docs/runbooks/or-credit-router-rollout.md
git commit -m "docs(runbooks): rollout sequence + rollback for OR credit router"
```

---

## Task 5: Fly secrets template

**Files:**
- Modify: [apps/api/fly.toml](../../apps/api/fly.toml) (or `fly.staging.toml` if separate)

Document required env vars so the deploy script fails loudly if anything is missing.

- [ ] **Step 1: Add `[env]` defaults + required-secret comments**

Append (or insert if `[env]` already exists):

```toml
[env]
LLM_ROUTER_MODE = "legacy"  # flip to "or" via `fly secrets set` after rollout step 4

# Required secrets (set via `fly secrets set`, never committed):
#   OPENROUTER_API_KEY  — from OR dashboard (see docs/runbooks/openrouter-byok.md)
#   BILLING_WORKER_URL  — https://<worker-name>.workers.dev
#   ANTHROPIC_API_KEY   — legacy backend; safe to keep so LLM_ROUTER_MODE=legacy still works post-cutover
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/fly.toml
git commit -m "chore(api): document LLM_ROUTER_MODE + BILLING_WORKER_URL in fly.toml"
```

---

## Task 6: End-to-end staging smoke (no commit, just a checklist run)

**Files:** none (executes the rollout runbook against staging)

- [ ] **Step 1**: Run runbook steps 1-5 against staging.
- [ ] **Step 2**: Verify the four observation criteria from runbook step 6 over a 24h window.
- [ ] **Step 3**: If anything red, stop and root-cause. Do NOT proceed to prod.
- [ ] **Step 4**: If green, proceed to runbook step 7 (prod).
- [ ] **Step 5**: After prod has been at `LLM_ROUTER_MODE=or` for one week with healthy metrics, file a follow-up to delete the `legacy` code path. Until then, keep both paths buildable.

---

## Phase C done — acceptance criteria

- ✅ `cd apps/web && npx vitest run src/lib/billing/` green
- ✅ `tiers.ts` retained but documented as dormant; no live imports
- ✅ BYOK runbook authored and verified (steps successfully executed once)
- ✅ Rollout runbook authored
- ✅ Staging at `LLM_ROUTER_MODE=or` for ≥ 24h with healthy metrics
- ✅ Prod at `LLM_ROUTER_MODE=or` with rollback lever proven working
- ✅ Adversarial review of the merged diff completed (per index-level T2 compensating control)

---

## Cross-phase final checklist

- [ ] [Phase A acceptance](2026-05-29-or-credit-router-plan-A-worker.md) green
- [ ] [Phase B acceptance](2026-05-29-or-credit-router-plan-B-python.md) green
- [ ] [Phase C acceptance](#phase-c-done--acceptance-criteria) green
- [ ] `/adversarial-review` run on the cumulative diff (T2 compensating control from [plan index](2026-05-29-or-credit-router-index.md))
- [ ] `/audit-spec docs/specs/2026-05-29-or-credit-router-design.md` shows ≥ 95% AC coverage
- [ ] Spec frontmatter `status: draft` → `status: shipped` after one prod week
