// LLM proxy helpers — origin allowlist, KV-backed rate limit + daily cost ceiling,
// Anthropic Messages pass-through. Wire protocol matches Anthropic verbatim.

export interface ProxyEnv {
  ANTHROPIC_API_KEY: string;
  ALLOWED_ORIGINS: string;
  RATE_LIMIT_PER_MIN: string;
  COST_CEILING_DAILY: string;
  ANTHROPIC_API_URL: string;
  ANTHROPIC_API_VERSION: string;
  LLM_AUTH_STYLE?: string;
  RATE_LIMIT_KV: KVNamespace;
}

export interface KVNamespace {
  get(key: string): Promise<string | null>;
  put(key: string, value: string, options?: { expirationTtl?: number }): Promise<void>;
}

export interface ProxyError {
  error: string;
  detail?: string;
}

const parseOrigins = (raw: string): string[] =>
  raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

export function isOriginAllowed(origin: string | null, env: ProxyEnv): boolean {
  if (!origin) return false;
  return parseOrigins(env.ALLOWED_ORIGINS).includes(origin);
}

export function corsHeaders(origin: string | null, env: ProxyEnv): HeadersInit {
  const allowed = isOriginAllowed(origin, env);
  return {
    'Access-Control-Allow-Origin': allowed && origin ? origin : 'null',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

export function jsonError(
  status: number,
  body: ProxyError,
  origin: string | null,
  env: ProxyEnv,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(origin, env),
    },
  });
}

const minuteKey = (ip: string): string => {
  const minute = Math.floor(Date.now() / 60_000);
  return `rl:${ip}:${minute}`;
};

const dayKey = (): string => {
  const day = new Date().toISOString().slice(0, 10);
  return `cost:${day}`;
};

export async function checkAndIncrementRateLimit(
  ip: string,
  env: ProxyEnv,
): Promise<{ ok: true } | { ok: false; reason: 'per_minute' | 'daily_ceiling' }> {
  const perMin = Number(env.RATE_LIMIT_PER_MIN) || 20;
  const dailyCeiling = Number(env.COST_CEILING_DAILY) || 10_000;

  const mk = minuteKey(ip);
  const current = Number((await env.RATE_LIMIT_KV.get(mk)) ?? '0');
  if (current >= perMin) return { ok: false, reason: 'per_minute' };

  const dk = dayKey();
  const daily = Number((await env.RATE_LIMIT_KV.get(dk)) ?? '0');
  if (daily >= dailyCeiling) return { ok: false, reason: 'daily_ceiling' };

  await env.RATE_LIMIT_KV.put(mk, String(current + 1), { expirationTtl: 120 });
  await env.RATE_LIMIT_KV.put(dk, String(daily + 1), { expirationTtl: 90_000 });
  return { ok: true };
}

interface AnthropicBody {
  model: string;
  max_tokens: number;
  messages: unknown[];
  stream?: boolean;
}

export function validateAnthropicBody(raw: unknown): raw is AnthropicBody {
  if (!raw || typeof raw !== 'object') return false;
  const b = raw as Record<string, unknown>;
  if (typeof b.model !== 'string' || !b.model) return false;
  if (typeof b.max_tokens !== 'number' || b.max_tokens <= 0) return false;
  if (!Array.isArray(b.messages) || b.messages.length === 0) return false;
  return true;
}

export async function forwardToAnthropic(body: AnthropicBody, env: ProxyEnv): Promise<Response> {
  const wantsStream = body.stream === true;
  const authHeader: Record<string, string> =
    env.LLM_AUTH_STYLE === 'bearer'
      ? { Authorization: `Bearer ${env.ANTHROPIC_API_KEY}` }
      : { 'x-api-key': env.ANTHROPIC_API_KEY };
  const upstream = await fetch(env.ANTHROPIC_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeader,
      'anthropic-version': env.ANTHROPIC_API_VERSION,
    },
    body: JSON.stringify(body),
  });

  if (wantsStream) {
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') ?? 'text/event-stream',
        'Cache-Control': 'no-store',
      },
    });
  }

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('Content-Type') ?? 'application/json',
    },
  });
}

export function clientIp(request: Request): string {
  return (
    request.headers.get('CF-Connecting-IP') ||
    request.headers.get('X-Forwarded-For')?.split(',')[0]?.trim() ||
    'unknown'
  );
}
