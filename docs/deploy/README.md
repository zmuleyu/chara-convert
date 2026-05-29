# chara-convert deployment runbook

> One-time setup + ongoing operations for the three deploy targets behind chara-convert v0.
> Roadmap context: [group_docs/roadmaps/chara-convert-roadmap-v1.0-2026-05-29.md](../../../aichat_group/group_docs/roadmaps/chara-convert-roadmap-v1.0-2026-05-29.md) M4 (公网可访问).

## Topology

```
studio.aichathub.uk/chara-convert/*  →  Cloudflare Pages   (apps/web)
chara-convert-shim.fly.dev/*          →  Fly.io machine    (apps/api)
chara-convert-billing.zmuleyu.workers.dev/*  →  Cloudflare Worker (workers/billing)
```

Web fetches FastAPI via `PUBLIC_API_BASE` env (`https://chara-convert-shim.fly.dev`) and the billing worker via `PUBLIC_BILLING_BASE` (`https://chara-convert-billing.zmuleyu.workers.dev`). Both set as Cloudflare Pages **build env vars**.

---

## One-time setup

### 1. Cloudflare Pages — `chara-convert-web`

```bash
# Local (one-time)
npx wrangler login
npx wrangler pages project create chara-convert-web --production-branch master
```

Then in Cloudflare dashboard:
- Bind custom domain `studio.aichathub.uk/chara-convert/*` (or add CNAME from existing studio.aichathub.uk zone to `chara-convert-web.pages.dev` if DNS is elsewhere).
- Set production build env vars:
  - `PUBLIC_API_BASE = https://chara-convert-shim.fly.dev`
  - `PUBLIC_BILLING_BASE = https://chara-convert-billing.zmuleyu.workers.dev`
- Enable Web Analytics (Settings → Web Analytics → Enable).

### 2. Fly.io — `chara-convert-shim`

```bash
flyctl auth login
flyctl apps create chara-convert-shim
# Fly will auto-detect apps/api/fly.toml on first deploy

# Pick ONE LLM backend secret (precedence: Anthropic > DeepSeek; mock test path always wins):
#   Anthropic (prod-grade):
flyctl secrets set ANTHROPIC_API_KEY=sk-ant-... -a chara-convert-shim
#   DeepSeek (cheap dev/staging, ~$0.14/M input tok):
flyctl secrets set DEEPSEEK_API_KEY=ds-... -a chara-convert-shim

flyctl deploy --config apps/api/fly.toml --remote-only
```

Install the matching SDK extra in `apps/api/Dockerfile` (or pyproject) before deploy:
- Anthropic backend: `pip install 'chara-convert[ai]'`
- DeepSeek backend: `pip install 'chara-convert[deepseek]'`

After first deploy, CI takes over via `superfly/flyctl-actions/setup-flyctl@master` + `FLY_API_TOKEN` GH secret.

### 3. Cloudflare Worker — `chara-convert-billing`

```bash
# Create the KV namespace once
npx wrangler kv:namespace create RATE_LIMIT_KV --workingDirectory workers/billing
# Copy the printed id (UUID) into workers/billing/wrangler.toml,
# replacing TBD-bind-on-first-deploy
npx wrangler deploy --workingDirectory workers/billing
```

CI deploys subsequent changes via `cloudflare/wrangler-action@v3` (workers-ci.yml).

---

## GitHub repo secrets (set once)

Repo → Settings → Secrets and variables → Actions:

| Secret | Used by | How to obtain |
|---|---|---|
| `CF_API_TOKEN` | Pages + Workers deploy | Cloudflare dashboard → My Profile → API Tokens → Custom token with `Account: Pages:Edit + Workers Scripts:Edit + Workers KV:Edit` |
| `CF_ACCOUNT_ID` | Pages + Workers deploy | Cloudflare dashboard → right sidebar (`ee1c...`) |
| `FLY_API_TOKEN` | Fly.io deploy | `flyctl auth token` |

GitHub repo **vars** (non-secret, for build override):
- `PUBLIC_API_BASE` — defaults to `https://chara-convert-shim.fly.dev` if unset
- `PUBLIC_BILLING_BASE` — defaults to `https://chara-convert-billing.zmuleyu.workers.dev` if unset

`ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` live only as **Fly.io secrets** — NOT in GitHub. CI tests always run with `CHARA_CONVERT_AI_MOCK`. Factory precedence inside the shim: `CHARA_CONVERT_AI_MOCK` > `ANTHROPIC_API_KEY` > `DEEPSEEK_API_KEY` > `none` (heuristic fallback).

---

## DNS — `studio.aichathub.uk`

Check delegation: `dig +short NS studio.aichathub.uk`.

- If Cloudflare-hosted: add `studio.aichathub.uk` as custom domain on the `chara-convert-web` Pages project (Cloudflare handles cert + routing).
- If elsewhere: add CNAME record `studio.aichathub.uk → chara-convert-web.pages.dev` (proxied) + add `studio.aichathub.uk` as custom domain in CF Pages.

Fallback during DNS provisioning: site is reachable at `https://chara-convert-web.pages.dev/chara-convert/` regardless of DNS state.

---

## Acceptance smoke (run after first triple deploy)

```bash
curl -sI https://studio.aichathub.uk/chara-convert/ | head -1
curl -sI https://studio.aichathub.uk/chara-convert/convert | head -1
curl -sI https://studio.aichathub.uk/chara-convert/pricing | head -1
curl -s https://chara-convert-shim.fly.dev/healthz
curl -s https://chara-convert-shim.fly.dev/api/platforms | jq '.sources | length'
curl -s https://chara-convert-billing.zmuleyu.workers.dev/api/billing/quota | jq
```

All five must return HTTP 200 / valid JSON / non-empty body before flipping the launch flag.

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Pages deploy stuck at "queued" | First-time project; CF still provisioning | Wait 60s, re-run job |
| `flyctl deploy` errors `app not found` | Step 2 above not done | `flyctl apps create chara-convert-shim` once |
| Worker 500 on `/api/billing/quota` | KV namespace not bound | Confirm `wrangler.toml` `id` is real UUID, not TBD placeholder |
| SSE truncated | CF Pages buffering proxied response | Don't proxy SSE through Pages — `PUBLIC_API_BASE` must point to Fly directly |
| CORS preflight 403 | apps/api CORS doesn't include current host | Update `apps/api/main.py` CORSMiddleware `allow_origins` |
