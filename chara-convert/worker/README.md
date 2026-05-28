# chara-convert LLM proxy Worker

Standalone Cloudflare Worker that proxies the Anthropic Messages API for
the chara-convert tool. Adds an Origin allowlist, KV-backed per-minute rate
limit, and a daily request ceiling on top of the upstream wire protocol
(which is otherwise byte-for-byte transparent, SSE included).

## Why this exists

The proxy used to live inside the aichathub Astro site at `/api/llm/proxy`.
That route was removed when aichathub returned to a pure-static Cloudflare
Pages deployment (Astro 6 + `@astrojs/cloudflare` 12 SSR returns 500; adapter
13 dropped Pages support). chara-convert is the only consumer of that proxy,
so the logic moved here.

Source is a verbatim port of `aichathub@fed7839:src/lib/llm-proxy.ts` with
the Astro `APIRoute` entry rewritten as a Worker `fetch` handler. See
[aichathub handoff](https://github.com/zmuleyu/aichathub/blob/claude/modest-payne-9719b2-H30Ej/collab/handoffs/2026-05-28-proxy-worker-migration.md)
for the migration design.

## Local development

```bash
cd chara-convert/worker
pnpm install
cp .dev.vars.example .dev.vars  # paste a real ANTHROPIC_API_KEY
pnpm dev                         # wrangler dev — local Worker on :8787
```

Run tests / typecheck:

```bash
pnpm test           # vitest, 9 cases
pnpm typecheck      # tsc --noEmit
```

## Deploy

```bash
wrangler login                              # browser OAuth
wrangler secret put ANTHROPIC_API_KEY       # paste sk-ant-…
wrangler deploy                             # → https://<name>.workers.dev
```

After deploy, smoke-test:

```bash
curl -X OPTIONS https://<name>.workers.dev \
  -H "Origin: http://localhost:7860" -i   # expect 204 + Access-Control-* headers
```

## Configuration (wrangler.toml)

### `ALLOWED_ORIGINS` (REQUIRED for prod)

Comma-separated Origin allowlist. Any other Origin gets 403. The default in
this repo (`http://localhost:4321,http://localhost:7860`) covers local Astro +
Gradio dev only. Edit `wrangler.toml` to add your real frontend domains, then
redeploy.

### `RATE_LIMIT_PER_MIN` / `COST_CEILING_DAILY`

Per-IP per-minute cap (default 20) and daily request ceiling (default 10000).
Both backed by the `RATE_LIMIT_KV` namespace.

### `ANTHROPIC_API_URL` / `ANTHROPIC_API_VERSION`

Forward target. Default points at `https://api.anthropic.com/v1/messages`
with version `2023-06-01`. To route through a DeepSeek-compatible endpoint
(test only), edit and redeploy.

### KV namespace

`wrangler.toml` reuses the namespace IDs that were attached to the old
aichathub Worker (account `24f44c02c89ded60aa44ae1f9491642f`). If you deploy
to a different Cloudflare account, create a new pair:

```bash
wrangler kv:namespace create RATE_LIMIT_KV
wrangler kv:namespace create RATE_LIMIT_KV --preview
```

…and paste the resulting IDs into `wrangler.toml`.

### Secret

`ANTHROPIC_API_KEY` must NOT be in `wrangler.toml`. Set it once with
`wrangler secret put ANTHROPIC_API_KEY`; local dev uses `.dev.vars`.

## Wiring chara-convert to this Worker

Once the Worker is live, point the chara-convert client at it:

```bash
export CHARA_CONVERT_API_BASE=https://<your-worker>.workers.dev
export CHARA_CONVERT_PROXY_ORIGIN=<one of your ALLOWED_ORIGINS values>
export ANTHROPIC_API_KEY=any-non-empty-placeholder   # real key lives in Worker secret
ccv convert tests/fixtures/_e2e_minimal.json --target fictionlab --ai
```

No code change in the Python client is required — `CHARA_CONVERT_API_BASE`
already drives the Anthropic SDK `base_url`, and `CHARA_CONVERT_PROXY_ORIGIN`
sets the `Origin` header that this Worker validates.

## Cut-over checklist (from upstream handoff)

1. Deploy this Worker + KV + secret; smoke-test OPTIONS / POST / SSE.
2. Point chara-convert's `CHARA_CONVERT_API_BASE` at the new Worker.
3. Verify a real `ccv --ai` run produces output.
4. **Only then** merge the aichathub static-site branch (which deletes the
   old `/api/llm/proxy` route). Doing step 4 before steps 1-3 leaves
   chara-convert with no working backend.
