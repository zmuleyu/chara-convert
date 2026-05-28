# chara-convert

AI character card conversion workbench. Reads cards from one platform's
export format, maps the fields to another platform's spec, and emits a
markdown report that highlights gaps you still need to fill in by hand.

**AI is optional.** The core conversion pipeline is pure-heuristic — name,
description, personality, dialogue examples, first message, lorebook entries,
CAI/Chai split-extras, etc. are all routed via `chara_convert/converter.py`
with no network calls. The `--ai` flag only fills the handful of layered
fields where there is genuinely no source data to map from (see the
[Heuristic vs AI fields](#heuristic-vs-ai-fields-fictionlab) table below).

## Installation

```bash
git clone https://github.com/zmuleyu/aichat_group
cd aichat_group/chara-convert

uv sync                  # heuristic-only (default — no AI, no webui)
uv sync --extra ai       # + Claude AI enrichment (anthropic SDK)
uv sync --extra web      # + Gradio web UI
uv sync --extra ai --extra web   # everything
```

Plain `uv sync` pulls only `click` and gives you a fully functional CLI for
conversion + gap analysis. Add extras only when you need them.

## Quickstart (no AI)

```bash
uv run ccv convert path/to/card.json --target fictionlab --out report.md
```

The report begins with a ready score and a gap summary. Example
([tests/fixtures/_e2e_out.md](tests/fixtures/_e2e_out.md)):

```markdown
# Character Card Conversion Report: → FictionLab

**Ready Score:** 23/100

## Gap Summary
- **Perfect match:** character.name, character.description, character.personality, scenario.first_message
- **Missing (required):** location.location_name, scenario.scenario_name, lore.piece_name, lore.content
```

Fields that need user input but couldn't be auto-derived show up as
`[MANUAL — paste or write content here]` placeholders in the output, so you
can search-and-replace your way through them.

Other useful commands:

```bash
uv run ccv list-platforms                 # show all known target slugs
uv run ccv diff card.json --target sillytavern_v2   # gap analysis only
uv run ccv webui                          # local Gradio UI (needs --extra web)
```

## Supported platforms

Source/target slugs (from `chara_convert/specs/*.toml`, exposed by
`ccv list-platforms`):

| Slug | Platform |
|------|----------|
| `agnai` | Agnai |
| `backyardai` | Backyard AI (Faraday) |
| `fictionlab` | FictionLab (layered: character / location / scenario / lore) |
| `janitorai` | Janitor AI |
| `nomi` | Nomi.ai |
| `novelai` | NovelAI |
| `risuai` | RisuAI |
| `saucepan` | Saucepan |
| `sillytavern_v2` | SillyTavern V2 |

## AI enrichment (optional)

Add the `--ai` flag to fill layered fields that have no heuristic source
(currently 4 fields — see table below). The backend is resolved at call
time from environment variables, in this precedence:

| Env var | Backend | Notes |
|---------|---------|-------|
| `CHARA_CONVERT_AI_MOCK=<text>` | Canned mock response | Highest precedence. Offline-safe, used by tests and local smoke runs. |
| `ANTHROPIC_API_KEY=sk-…` | Anthropic Claude (direct) | Requires the `[ai]` extra. |
| `CHARA_CONVERT_API_BASE=<url>` | Routes Anthropic SDK through a custom base URL | Use with a self-hosted proxy (see [worker/](worker/README.md)). |
| `CHARA_CONVERT_PROXY_ORIGIN=<origin>` | Injects an `Origin` header on every Anthropic request | Needed when the proxy enforces an Origin allowlist. |
| `CHARA_CONVERT_PROXY_AUTH_TOKEN=<jwt>` | Injects `X-Creem-Token` header | For proxies that require server-token auth. |

Offline demo (no network, no real key):

```bash
CHARA_CONVERT_AI_MOCK='example dialogue placeholder' \
  uv run ccv convert tests/fixtures/_e2e_minimal.json --target fictionlab --ai
```

Without any of those env vars set, `ccv --ai` exits with an actionable
error (`--ai requested but no AI backend configured. Set ANTHROPIC_API_KEY
or CHARA_CONVERT_AI_MOCK and retry.`). The webui degrades gracefully —
ticking the AI checkbox without a backend produces heuristic output plus a
warning, not a crash.

## Heuristic vs AI fields (FictionLab)

The FictionLab spec splits a character card across 4 layers. Heuristic
routing is in `chara_convert/converter.py::_fictionlab_field_value`.

| Layer | Field | Heuristic source | AI fills (when `--ai`) |
|-------|-------|------------------|------------------------|
| character | `name` | `card.name` | — |
| character | `description` | CAI/Chai split extras → `card.description` | — |
| character | `personality` | `card.personality` | — |
| character | `example_dialogue` | `card.mes_example` | yes, if source is empty |
| character | `appearance` | — | yes (AI-only) |
| location | `location_description` | CAI definition_location | — |
| location | `location_name` | — | requires manual input |
| location | `atmosphere` | — | requires manual input |
| scenario | `first_message` | `card.first_mes` | — |
| scenario | `scenario_intro` | `card.scenario` | yes, if source is empty |
| scenario | `custom_instructions` | CAI/Chai instruction extras | — |
| scenario | `scenario_name` | — | requires manual input |
| scenario | `linked_characters` | — | requires manual input |
| scenario | `linked_location` | — | requires manual input |
| lore | `content` | CAI definition_lore | — |
| lore | `piece_name` | — | requires manual input |
| lore | `activation_condition` | — | requires manual input |

Fields marked "requires manual input" remain as `[MANUAL — paste or write
content here]` even when `--ai` is set; they are pure user-supplied data
with no reliable heuristic or AI inference.

For flat (non-layered) targets like SillyTavern V2 or Janitor AI, every
required field without a source mapping is listed in the report's "Missing
(required)" section.

## Self-hosted LLM proxy (optional)

If you don't want to ship API keys to every chara-convert user, run the
bundled Cloudflare Worker as your team's shared backend:

```bash
cd worker
pnpm install
wrangler secret put ANTHROPIC_API_KEY
wrangler deploy
```

Then point chara-convert clients at it via `CHARA_CONVERT_API_BASE`. See
[worker/README.md](worker/README.md) for the full deployment + ALLOWED_ORIGINS
configuration walkthrough.

## Development

```bash
uv sync --extra ai --extra web        # install everything
uv run pytest -x -q                   # run the Python test suite
uv run ruff check .                   # lint (if configured)
```

Worker subproject lives at [worker/](worker/) and has its own toolchain
(`pnpm install` / `pnpm test`).

## Related

- [docs/specs/2026-05-28-llm-proxy-route-and-origin-workaround.md](../docs/specs/2026-05-28-llm-proxy-route-and-origin-workaround.md)
  — env contract + deprecation timeline for the legacy Origin gate.
- [worker/README.md](worker/README.md) — self-hosted proxy deployment.
