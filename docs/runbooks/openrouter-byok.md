# OpenRouter BYOK Configuration

**Owner:** ops (zmuleyu)
**Last verified:** TBD on first production run
**Related:** [docs/specs/2026-05-29-or-credit-router-design.md](../specs/2026-05-29-or-credit-router-design.md)

## Why

OpenRouter routes each request to the cheapest available provider. With BYOK
(Bring Your Own Key) for DeepSeek + Anthropic configured in the OR dashboard,
OR forwards traffic through *our* provider keys and bills only the 5.5%
routing fee. Without BYOK, OR bills retail (~30–60% markup over direct).

Spec §Prerequisites §2: BYOK is "strongly recommended day 1 to capture
direct-provider rates; system functions without BYOK (OR billed at retail)."

## Prerequisites

- OpenRouter account at https://openrouter.ai
- DeepSeek API key (https://platform.deepseek.com) — separate from the existing
  Fly `DEEPSEEK_API_KEY` secret (that one stays for the `legacy` router path)
- Anthropic API key (separate from the existing Fly `ANTHROPIC_API_KEY` secret,
  same reason)

## Setup steps

1. Log into OpenRouter dashboard → **Integrations**.
2. For each provider (DeepSeek, Anthropic):
   - **Add Integration** → select provider.
   - Paste the API key.
   - **Save**. OR verifies with a low-cost test call before activating.
3. **Settings → Default Provider Order**: leave at "Lowest price" (matches the
   `provider.sort=price` parameter the router sends per-request — see
   [chara-convert/chara_convert/llm/openrouter.py](../../chara-convert/chara_convert/llm/openrouter.py)).
4. **Settings → Keys** → **Generate API Key**. Copy the value. This is the
   `OPENROUTER_API_KEY` for Fly secrets in the [rollout runbook](or-credit-router-rollout.md).
5. Verify BYOK is active by inspecting a sample call:

   ```bash
   curl https://openrouter.ai/api/v1/chat/completions \
     -H "Authorization: Bearer $OR_KEY" \
     -H "content-type: application/json" \
     -d '{"model":"deepseek/deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":5,"usage":{"include":true}}'
   ```

   Look at `usage.cost` in the response. Should reflect direct DeepSeek pricing
   ($0.14/M input + $0.28/M output) plus a small OR fee — not the retail OR
   markup. If cost looks 30%+ higher than the table in
   [chara-convert/chara_convert/llm/pricing.py](../../chara-convert/chara_convert/llm/pricing.py),
   the BYOK entry is not active for that provider.

## Key rotation

| What | How |
|---|---|
| Provider key (DeepSeek/Anthropic) | Rotate in provider dashboard → update the integration entry in OR dashboard. No Fly redeploy needed; OR proxies transparently. |
| OR key | Generate new in OR Settings → Keys → `fly secrets set --app chara-convert-shim OPENROUTER_API_KEY=...` → revoke old in OR dashboard. |

## Failure mode

If BYOK is misconfigured (e.g. a revoked provider key on OR's side), OR falls
back to its own retail keys for that provider and bills accordingly. Traffic
is **not** interrupted — only cost shape changes.

Detection paths:

- Monthly OR pricing drift check: [scripts/pricing_drift_check.py](../../scripts/pricing_drift_check.py)
  flags >20% deviation between the in-repo `PRICING_TABLE` and live OR rates.
- OR dashboard → **Activity** page: cost-per-call spike on the affected
  provider model.
- Python router emits `credit.cost_missing` when the OR response omits
  `usage.cost`. A sustained spike there points at OR-side issues (including
  silent BYOK fallback) — see [chara-convert/chara_convert/llm/router.py](../../chara-convert/chara_convert/llm/router.py).

No code change required for fallback recovery: fix the provider key in OR,
costs return to direct-billed on the next request.
