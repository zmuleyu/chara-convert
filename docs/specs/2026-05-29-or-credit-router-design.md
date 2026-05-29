---
title: OpenRouter-unified Credit Router
date: 2026-05-29
architectModel: opus
status: draft
supersedes: 2026-05-29-deepseek-llm-backend.md (factory precedence only)
---

# OpenRouter-unified Credit Router

## Decision

Route 100% of paying-user LLM traffic through a single **OpenRouter (OR)** client. BYOK to DeepSeek + Anthropic configured in OR dashboard so we pay direct-provider token rates plus OR's ~5.5% routing fee. Drop multi-provider in-app abstraction. Existing `deepseek.py` / `anthropic.py` clients retained only for mock / dev / test paths.

Users see no model selection. Credit balance gates access:
- default → **high** model class (Claude-class)
- balance insufficient for high but ≥ low → **low** model class (DeepSeek-class)
- balance < low → 402

Subscription tier (free/creator/studio) is **dropped** as a routing input. Pure pay-as-you-go with new-user grant.

## Key trade-offs

- **All-OR vs. hybrid direct+OR** → all-OR. At early stage operational simplicity (single integration, single billing surface, OR's built-in fallback) >> 5.5% routing fee. Pivot back if monthly LLM spend > ~$5k or OR uptime becomes a documented incident.
- **Pure credit vs. credit + subscription tier** → pure credit. User's stated mental model is "credit determines model"; subscription complexity (Creem cutover Oct 2026) is dead weight at the experimentation stage. Adding monthly grant later is a superset.
- **Hold + true-up vs. post-debit** → hold + true-up. Paying users must not be able to burn through balance via concurrent requests. Cost: one extra Worker round-trip per request, one extra D1 table.
- **D1 vs. KV for ledger** → D1. Credit hold/debit/refund needs transactional read-modify-write; KV's eventual consistency loses money.
- **Model strings in code vs. config** → code. Fallback chain changes get git review + deploy audit; no runtime tunable.

## Architecture

```
Web (CF Pages)  ──POST /ai/enrich  + X-User-Id──►  chara-convert API (Fly)
                                                    │
                                                    ├─► billing Worker (CF + D1)
                                                    │     credit balance + hold lifecycle
                                                    │
                                                    └─► openrouter.ai/api/v1
                                                          (BYOK: DeepSeek, Anthropic)
```

### Module ownership

| File | Status | Purpose |
|---|---|---|
| `chara_convert/llm/openrouter.py` | new | OR client (OpenAI-compatible against `openrouter.ai/api/v1`) |
| `chara_convert/llm/router.py` | new | model class selection + OR payload assembly |
| `chara_convert/llm/credit_client.py` | new | HTTP client to billing Worker `/credit/*` endpoints |
| `chara_convert/llm/pricing.py` | new | `PRICING_TABLE` constant + USD↔credit converters |
| `chara_convert/llm/factory.py` | edit | precedence `mock > openrouter > none`; deepseek/anthropic dropped from prod chain |
| `apps/api/routes/ai_enrich.py` | edit | accept `X-User-Id`, call router with hold/debit lifecycle |
| `chara_convert/llm/{deepseek,anthropic,mock}.py` | keep | dev/test/mock only |
| `workers/billing/src/index.ts` | edit | add 4 credit endpoints; bind D1 |
| `workers/billing/src/credit.ts` | new | hold/debit/refund/balance logic + transactions |
| `workers/billing/migrations/0001_credit_ledger.sql` | new | D1 schema (3 tables below) |
| `workers/billing/src/quota.ts` | keep | IP quota for anonymous users (DoS layer) |
| `apps/web/src/lib/billing/tiers.ts` | keep, dormant | retained for future SaaS re-enable |
| `apps/web/src/lib/billing/client.ts` | edit | switch to balance polling endpoint |
| `pyproject.toml` | edit | drop `[deepseek]` extra (openai SDK already needed by OR client) |

## Prerequisites (explicit)

1. **User identity system** — `X-User-Id` header that the API can trust. Out of scope here. Without it, credit accounting is impossible. Spec will not deploy until auth exists. Assumed shape: opaque string (UUID/ULID) issued at signup, passed in every request.
2. **OR dashboard BYOK keys** — DeepSeek + Anthropic configured by hand. *Strongly recommended day 1* to capture direct-provider rates; system functions without BYOK (OR billed at retail). Documented in `docs/runbooks/openrouter-byok.md` (new, not part of code spec).
3. **CF D1 binding** — `wrangler.toml` declares `[[d1_databases]]` with binding `CREDIT_DB`. Migration runs via `wrangler d1 migrations apply`.

## Routing policy

```python
# Default behavior: always attempt the highest class the user can afford.
# No per-request quality hint from the client; class is purely affordability-driven.
def pick_model_class(balance: int, estimated_high: int, estimated_low: int) -> str:
    if balance >= estimated_high: return "high"
    if balance >= estimated_low:  return "low"
    raise InsufficientCredit()
```

### Model config (frozen)

```python
MODEL_BY_CLASS = {
    "low": {
        "primary":  "deepseek/deepseek-chat",
        "fallback": ["deepseek/deepseek-chat", "moonshotai/kimi-k2"],
    },
    "high": {
        "primary":  "anthropic/claude-3.5-sonnet",
        "fallback": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
    },
}
# invariant: primary == fallback[0]
```

### OR request shape

```python
{
    "model": cfg["primary"],
    "models": cfg["fallback"],          # OR auto-failover
    "provider": {"sort": "price", "allow_fallbacks": True},
    "messages": [...],
    "stream": True,
    "usage": {"include": True},         # final SSE event carries cost
    "max_tokens": 800,
    "temperature": 0.7,
}
```

## Credit accounting

**Unit:** `1 credit = $0.0001 USD`. Internal arithmetic is integer-only; USD↔credit conversion happens at boundaries.

**Lifecycle:** hold → true-up debit OR refund.

```
T0  estimate_max_credit = ceil((input_tokens·p_in + max_tokens·p_out) / 1e6 / 0.0001)
    POST /credit/hold  →  {holdId, newBalance}   # 402 if insufficient

T1  OR streamed SSE → forwarded to client

T2a stream complete + usage.cost present:
    actual = ceil(usage.cost / 0.0001)
    POST /credit/debit {holdId, actualAmount: actual}

T2b stream complete + usage.cost missing:
    actual = ceil(local_estimate(prompt_tokens, completion_tokens) / 0.0001)
    POST /credit/debit  + metric `credit.cost_missing` += 1

T2c stream failed / client disconnect:
    POST /credit/refund {holdId}

cron: every 10min, refund hold rows where status='open' AND created_at < now-1h
```

### D1 schema (`workers/billing/migrations/0001_credit_ledger.sql`)

```sql
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

### Invariants

1. For every user: `sum(credit_ledger.delta) == balance + held`
2. Every `credit_hold` row eventually transitions to `debited` or `refunded`
3. `credit_balance.balance + credit_balance.held >= 0` always

### Billing Worker endpoints

| Method | Path | Body | Returns | Notes |
|---|---|---|---|---|
| GET  | `/api/billing/credit/balance` | — | `{balance, held}` | requires X-User-Id |
| POST | `/api/billing/credit/hold` | `{amount}` | `{holdId, newBalance}` or 402 | atomic |
| POST | `/api/billing/credit/debit` | `{holdId, actualAmount}` | `{newBalance}` | atomic; release hold + deduct actual |
| POST | `/api/billing/credit/refund` | `{holdId}` | `{newBalance}` | atomic |

All use D1 `BEGIN..COMMIT` transactions.

## Error handling

| Failure point | Behavior | User-visible |
|---|---|---|
| balance < estimated_low | 402 before OR call | "insufficient credit" |
| OR primary 5xx/timeout | OR auto-fallback (transparent) | none |
| OR full chain failed | refund hold, 503 | "service unavailable, retry" |
| Mid-stream break | refund hold, SSE `event: error` | partial text + "generation interrupted" |
| Client disconnect | refund hold | — |
| `usage.cost` missing | local estimate debit + metric | none |
| Orphan hold (settle failed) | cron refund | — |

SSE error frame:
```
event: error
data: {"code": "or_unavailable", "message": "AI service unavailable"}
```

## Migration & rollout

Sequence (out-of-order = brief production breakage):

1. Apply D1 migration; deploy billing Worker with new endpoints (keep old IP quota endpoints intact)
2. Deploy chara-convert API with feature flag `LLM_ROUTER_MODE=legacy|or` (default `legacy`)
3. Configure OR BYOK (DeepSeek + Anthropic) in dashboard
4. Manually grant N credit to test accounts via `wrangler d1 execute`
5. Staging: flip flag → run smoke (low-class request, verify hold/debit/balance) → flip prod
6. Monitor `credit.cost_missing` and OR fallback hit rate for 1 week → tune

## Testing strategy

- **Unit**: `router.pick_model_class` (balance × estimates table), `pricing.usd_to_credit` (boundary rounding)
- **Integration (respx)**: mock OR's SSE format including final `usage.cost` event; verify hold → debit and hold → refund paths end-to-end
- **Contract**: pydantic models for billing Worker endpoints match TS interfaces (snapshot test on both sides)
- **CI smoke**: 1 real OR call against `deepseek/deepseek-chat`, max_tokens=20, assert `usage.cost > 0`; budget cap $0.01/run
- **Drift guard**: monthly cron pulls OR pricing API; diff vs. `PRICING_TABLE`; alert (not block) if any entry drifts >20%

## Pricing table seed (review before merging)

```python
# USD per 1M tokens; seeded from OR list 2026-05-29
PRICING_TABLE = {
    "low": {
        "deepseek/deepseek-chat":   {"input": 0.14, "output": 0.28},
        "moonshotai/kimi-k2":       {"input": 0.60, "output": 2.50},
        "worst_case":               {"input": 0.60, "output": 2.50},  # used for hold sizing
    },
    "high": {
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "openai/gpt-4o":               {"input": 2.50, "output": 10.00},
        "worst_case":                  {"input": 3.00, "output": 15.00},
    },
}
USD_PER_CREDIT = 0.0001  # 1 credit
```

## Out of scope

- User authentication system (prereq)
- Topup payment flow (Creem integration, separate spec)
- Free-tier daily grant policy (admin tool only at v1; future cron)
- Multi-region OR endpoint routing
- Privacy / data-retention agreements with OR (creative writing only; revisit if expanding to PII)
