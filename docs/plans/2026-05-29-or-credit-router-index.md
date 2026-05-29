---
title: OR Credit Router — Plan Index
spec: docs/specs/2026-05-29-or-credit-router-design.md
date: 2026-05-29
architectModel: opus
tier: 2
tierReason: money correctness + atomic D1 transactions + multi-component coupling
planReview: skipped-user-instruction-override
planReviewNote: model-dispatch kind=plan-review not shipped; user invoked writing-plans with "work without stopping for clarifying questions"; tier=2 normally requires 1 plan-reviewer + adversarial-review per ~/.claude/plan-extensions.md §Plan Review Handoff. Run /adversarial-review on each sub-plan before execution.
---

# OR Credit Router Implementation — Plan Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement each sub-plan task-by-task. Sub-plans use checkbox (`- [ ]`) syntax.

**Goal:** Route 100% of paying-user LLM traffic through OpenRouter with credit-gated model class selection and hold/debit accounting.

**Architecture:** Three loosely-coupled sub-systems — (1) CF Worker + D1 ledger, (2) Python OR client + router in chara-convert API, (3) Astro web client balance polling. Each sub-plan produces working, independently-testable software.

**Tech Stack:** Cloudflare Workers (TS), D1 (SQLite), Python 3.11 + FastAPI, OpenRouter OpenAI-compatible API, Astro/React web.

---

## Sub-plans

| Phase | Plan | Dependencies | Verification |
|---|---|---|---|
| A | [2026-05-29-or-credit-router-plan-A-worker.md](2026-05-29-or-credit-router-plan-A-worker.md) | none | miniflare D1 vitest + curl smoke |
| B | [2026-05-29-or-credit-router-plan-B-python.md](2026-05-29-or-credit-router-plan-B-python.md) | A's endpoint contract (mockable) | pytest + respx OR mock + 1 real CI smoke |
| C | [2026-05-29-or-credit-router-plan-C-rollout.md](2026-05-29-or-credit-router-plan-C-rollout.md) (10 tasks after 2026-05-29 amendment) | A + B deployed | astro check + vitest + staging flip + balance poll smoke |

**Phase C amendment 2026-05-29**: original plan only covered `client.ts` rewrite; preview revealed 4 additional consumers of `tier/aiCap/aiUsed` (AiAssistPanel, UpgradeCTA, pricing.astro, docs.astro). Added Tasks 1.5 / 2.5 / 2.6 / 5.5 / 5.6 / 5.7 to cover the widened scope per user decision (pricing → stub / UpgradeCTA → LowCreditCTA / AiAssistPanel → balance gate).

Execute A → B → C strictly in order. B uses a fake Worker (in-process FastAPI mount or respx) so it does not require A deployed.

## Spec ↔ reality path corrections

The spec uses idealized paths; the repo nests `chara_convert/` one level deep. Translations:

| Spec path | Real path (from workspace root `D:/projects/aichat_group/chara-convert/`) |
|---|---|
| `chara_convert/llm/openrouter.py` | [chara-convert/chara_convert/llm/openrouter.py](../../chara-convert/chara_convert/llm/openrouter.py) |
| `chara_convert/llm/router.py` | [chara-convert/chara_convert/llm/router.py](../../chara-convert/chara_convert/llm/router.py) |
| `chara_convert/llm/credit_client.py` | [chara-convert/chara_convert/llm/credit_client.py](../../chara-convert/chara_convert/llm/credit_client.py) |
| `chara_convert/llm/pricing.py` | [chara-convert/chara_convert/llm/pricing.py](../../chara-convert/chara_convert/llm/pricing.py) |
| `chara_convert/llm/factory.py` | [chara-convert/chara_convert/llm/factory.py](../../chara-convert/chara_convert/llm/factory.py) |
| `apps/api/routes/ai_enrich.py` | [apps/api/routes/ai_enrich.py](../../apps/api/routes/ai_enrich.py) (unchanged path) |
| `workers/billing/src/index.ts` | [workers/billing/src/index.ts](../../workers/billing/src/index.ts) (unchanged path) |
| `workers/billing/src/credit.ts` | [workers/billing/src/credit.ts](../../workers/billing/src/credit.ts) (unchanged path) |
| `workers/billing/migrations/0001_credit_ledger.sql` | [workers/billing/migrations/0001_credit_ledger.sql](../../workers/billing/migrations/0001_credit_ledger.sql) (new dir) |
| `pyproject.toml` | [chara-convert/pyproject.toml](../../chara-convert/pyproject.toml) (the package one, NOT `apps/api/pyproject.toml`) |

## Prerequisites (block rollout, not implementation)

1. **`X-User-Id` trusted source**: not implemented. Sub-plan B writes the code to read the header and 401 if missing; staging/prod cutover blocked until an auth system issues + verifies these IDs. Tracked separately; do not block coding.
2. **OR dashboard BYOK**: manual config of DeepSeek + Anthropic keys. Runbook authored in Phase C. Without BYOK the system still runs but bills at OR retail rates.
3. **D1 binding in wrangler.toml**: created in Phase A Task 1.

## Risk-tier compensating controls

- All transactional logic (hold/debit/refund) ships with property-based integer-conservation tests (invariant 1: `sum(ledger.delta) == balance + held` per user).
- Worker endpoints write to `credit_ledger` *inside* the same `db.batch()` as the balance mutation (D1 batches are transactional). The conservation invariant test forces interleaved hold/debit/refund sequences and asserts the invariant holds after each step.
- After all three sub-plans GREEN, run `/adversarial-review` on the diff before promoting `LLM_ROUTER_MODE=or` past staging.

## Contract testing (spec §Testing strategy "Contract: pydantic ↔ TS")

The spec asks for "snapshot test on both sides". Rather than introduce a shared schema source, the contract is tested *bidirectionally*:

- Server-side (Phase A Task 9, `test/endpoints.test.ts`): exercises every 2xx/4xx envelope shape against the live Worker fetch handler.
- Client-side (Phase B Tasks 2 + 9, `test_credit_client.py` + `test_ai_enrich_lifecycle.py`): exercises the same envelopes via respx mocks of the Worker.

If either side drifts, the other suite fails. Acceptance: both suites must reference identical literal JSON shapes (`holdId`, `newBalance`, `actualAmount`, `balance`, `held`, `code`). Reviewer (or `/adversarial-review`) should diff the two test files looking for shape divergence before sign-off.

## Out of scope (carried from spec)

User auth (prereq), Creem topup flow, free-tier daily grant cron, multi-region OR routing, OR data-retention agreement.
