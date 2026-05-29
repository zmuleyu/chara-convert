---
type: pickup-handoff
project: chara-convert
branch: feat/or-credit-router
last_commit: 509c6a1
status: ready-for-implementer-dispatch
phase: pre-execution
---

# OR Credit Router — Session Pickup

## TL;DR for next session

Branch `feat/or-credit-router` carries the spec + 4 plan files (3 sub-phases). No implementation code written yet. Next step: invoke subagent-driven-development on Phase A Task 1 (`D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-A-worker.md`).

Total task count after Phase C amendment: **33 tasks** (A: 12, B: 11, C: 10).

## How to resume

In a fresh Claude Code session, paste:

```
继续 @D:/projects/aichat_group/chara-convert/collab/handoffs/2026-05-29-or-credit-router-pickup.md
```

Or run directly:

```
/Skill subagent-driven-development D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-A-worker.md
```

## Authoritative artifacts on disk

| What | Path |
|---|---|
| Design spec | [D:/projects/aichat_group/chara-convert/docs/specs/2026-05-29-or-credit-router-design.md](D:/projects/aichat_group/chara-convert/docs/specs/2026-05-29-or-credit-router-design.md) |
| Plan index | [D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-index.md](D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-index.md) |
| Phase A plan (Worker + D1) | [D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-A-worker.md](D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-A-worker.md) |
| Phase B plan (Python LLM router) | [D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-B-python.md](D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-B-python.md) |
| Phase C plan (Web + rollout) | [D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-C-rollout.md](D:/projects/aichat_group/chara-convert/docs/plans/2026-05-29-or-credit-router-plan-C-rollout.md) |
| UI baseline screenshots | [D:/projects/aichat_group/chara-convert/docs/plans/preview/](D:/projects/aichat_group/chara-convert/docs/plans/preview/) |

## What the previous session authorized (don't re-ask)

User explicitly said "全部授权，按照你的建议执行" — pre-approved:
1. Working on branch `feat/or-credit-router` (already created)
2. Implementers committing per-task per the plan's `git commit` steps
3. Running all three phases A → B → C sequentially
4. Skipping plan-review dispatch (planReview: skipped-user-instruction-override on index frontmatter); user accepts the T2 compensating-control gap will be closed by `/adversarial-review` on each sub-plan before merge

## Phase C scope was widened mid-planning

User asked for browser preview before implementation. Preview revealed `useBilling` is consumed in 4 more places than the original Phase C plan covered. User picked options 1b / 2a / 3a from a 3-question proposal:

- **1b** pricing.astro → "Top-up coming soon" stub (no credit packs designed yet; pending Creem cutover Oct 2026)
- **2a** UpgradeCTA → LowCreditCTA (balance < MIN_BALANCE_TO_TRY threshold)
- **3a** AiAssistPanel pre-reads balance, locally disables button when low

Result: Phase C amendment commit 509c6a1 added tasks 1.5 / 2.5 / 2.6 / 5.5 / 5.6 / 5.7. Old Phase C was 6 tasks, new is 10 tasks.

## Repo gotchas the implementer must know

1. **Nested layout**: `chara_convert/llm/*.py` actually lives at `D:/projects/aichat_group/chara-convert/chara-convert/chara_convert/llm/`. Plan index has the full translation table.
2. **Two pyproject.toml** files: `chara-convert/pyproject.toml` (the Python package — spec's `pyproject.toml` refers to this) and `apps/api/pyproject.toml` (the FastAPI shim — needs `respx` added per Phase B Task 7).
3. **wrangler.toml** binding placeholder: Phase A Task 1 Step 3-4 run `wrangler d1 create` which needs CF auth + creates real CF resources. If `npx wrangler whoami` shows no auth, the implementer should leave `REPLACE_AFTER_CREATE` placeholders and report DONE_WITH_CONCERNS — local `--local` D1 (used in tests) doesn't need real UUIDs.
4. **`LLMClient` base is sync, OR adds async**: `openrouter.py` keeps the sync `complete()` for LLMClient compatibility AND adds an async `stream_chat()` generator for the API route. Phase B Task 4 covers both paths.
5. **Existing `index.ts` has 4 endpoint stubs** + `quota.ts` for IP rate limiting — these must continue working post-Phase A (Phase A Task 9 keeps them).

## Risks still open

- **`X-User-Id` trust source not built**: code reads the header but no auth issues/verifies it. Blocks staging/prod cutover (Phase C Task 6). Does NOT block A/B implementation.
- **OR BYOK manual setup**: Phase C Task 3 runbook authoring is in the plan; actual dashboard config is human work.
- **Plan-review skipped**: T2 compensating control = run `/adversarial-review` on each phase's diff before promoting `LLM_ROUTER_MODE=or` past staging.

## Recommended dispatch sequence

Strictly serial (CLAUDE.md: "max 1 agent at a time on this machine"). For each of 33 tasks:

1. Dispatch implementer subagent with the full task text + repo gotchas above
2. After DONE, dispatch spec-reviewer subagent
3. After ✅, dispatch code-quality-reviewer subagent
4. After ✅, mark TodoWrite complete and move to next

TodoWrite list of all 33 tasks is in the previous session's state but not persisted to disk — easiest to re-create from the plan files in the new session.

## What NOT to do

- Do NOT switch to master or rebase onto it without explicit user OK.
- Do NOT skip review stages even when the implementer says it's trivial.
- Do NOT dispatch multiple implementers in parallel (CLAUDE.md feedback rule).
- Do NOT touch `apps/web/src/lib/billing/tiers.ts` content — it's intentionally dormant.
- Do NOT design credit-pack prices in pricing.astro; the stub is the deliberate answer until Creem lands.
