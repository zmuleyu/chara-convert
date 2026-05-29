# chara-convert

Character card converter (web + API).

> Extracted from `zmuleyu/aichat_group` on 2026-05-28 via `git filter-repo`.
> Pre-extraction snapshot tagged as `pre-shell-group-migration`.

## Layout
- `chara-convert/` — converter core (Python)
- `apps/api/` — FastAPI shim
- `apps/web/` — Astro frontend (islands architecture)
- `workers/billing/` — Cloudflare Worker, quota + 501 stubs (Creem cutover 2026-10)

See per-app READMEs for run instructions.

## LLM backends

The `chara_convert.llm.factory.build_ai_client_or_none()` helper picks an LLM client at runtime from env vars (first match wins):

| Env var | Backend | Extra | Use case |
|---|---|---|---|
| `CHARA_CONVERT_AI_MOCK=<canned>` | `MockLLMClient` | (built-in) | tests / smoke / offline |
| `ANTHROPIC_API_KEY=sk-ant-...` | `AnthropicClient` (Claude) | `pip install 'chara-convert[ai]'` | prod |
| `DEEPSEEK_API_KEY=ds-...` | `DeepSeekClient` (OpenAI-compat) | `pip install 'chara-convert[deepseek]'` | cheap dev/staging |
| _(none)_ | heuristic fallback | — | no AI features |

Override the model name via `CHARA_CONVERT_MODEL` and the base URL via `CHARA_CONVERT_API_BASE` (both backends respect them).

## Production targets

| Component | Target | Status |
|---|---|---|
| Pages (web) | `studio.aichathub.uk/chara-convert/` → `chara-convert-web.pages.dev` | project created; first deploy gated on CF_API_TOKEN GH secret |
| Shim (api) | `chara-convert-shim.fly.dev` | app not yet created (M4 pending) |
| Billing (worker) | `chara-convert-billing.zmuleyu.workers.dev` | live (Version `f6214023`) |

Acceptance smoke: `bash scripts/smoke.sh` (overrides via `PAGES_BASE` / `API_BASE` / `BILLING_BASE`).

Deploy runbook: [docs/deploy/README.md](docs/deploy/README.md). Roadmap (M0-M9) lives outside this repo in the local `aichat_group` shell-group workspace.
