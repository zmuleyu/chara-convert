import { afterEach, describe, expect, it, vi } from 'vitest';

import handler from '../src/index';
import type { KVNamespace, ProxyEnv } from '../src/llm-proxy';

const ALLOWED = 'https://example.test';

function makeKV(initial: Record<string, string> = {}): KVNamespace & { store: Map<string, string> } {
  const store = new Map(Object.entries(initial));
  return {
    store,
    async get(key) {
      return store.get(key) ?? null;
    },
    async put(key, value) {
      store.set(key, value);
    },
  } as KVNamespace & { store: Map<string, string> };
}

function makeEnv(overrides: Partial<ProxyEnv> = {}): ProxyEnv {
  return {
    ANTHROPIC_API_KEY: 'sk-test',
    ALLOWED_ORIGINS: ALLOWED,
    RATE_LIMIT_PER_MIN: '20',
    COST_CEILING_DAILY: '10000',
    ANTHROPIC_API_URL: 'https://api.anthropic.test/v1/messages',
    ANTHROPIC_API_VERSION: '2023-06-01',
    LLM_AUTH_STYLE: 'bearer',
    RATE_LIMIT_KV: makeKV(),
    ...overrides,
  };
}

function buildRequest(
  init: { method: string; origin?: string | null; body?: unknown; bodyText?: string; ip?: string } = {
    method: 'POST',
  },
): Request {
  const headers: Record<string, string> = { 'CF-Connecting-IP': init.ip ?? '1.2.3.4' };
  if (init.origin) headers.Origin = init.origin;
  let body: BodyInit | undefined;
  if (init.bodyText !== undefined) {
    body = init.bodyText;
    headers['Content-Type'] = 'text/plain';
  } else if (init.body !== undefined) {
    body = JSON.stringify(init.body);
    headers['Content-Type'] = 'application/json';
  }
  return new Request('https://worker.test/', { method: init.method, headers, body });
}

const validBody = {
  model: 'claude-haiku-4-5',
  max_tokens: 16,
  messages: [{ role: 'user', content: 'hi' }],
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('chara-convert llm-proxy worker', () => {
  it('OPTIONS preflight returns 204 with CORS headers for allowed origin', async () => {
    const res = await handler.fetch(buildRequest({ method: 'OPTIONS', origin: ALLOWED }), makeEnv());
    expect(res.status).toBe(204);
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe(ALLOWED);
    expect(res.headers.get('Access-Control-Allow-Methods')).toContain('POST');
    expect(res.headers.get('Vary')).toBe('Origin');
  });

  it('GET is rejected with 405 method_not_allowed', async () => {
    const res = await handler.fetch(buildRequest({ method: 'GET', origin: ALLOWED }), makeEnv());
    expect(res.status).toBe(405);
    expect(await res.json()).toEqual({ error: 'method_not_allowed' });
  });

  it('POST from disallowed Origin returns 403 origin_not_allowed', async () => {
    const res = await handler.fetch(
      buildRequest({ method: 'POST', origin: 'https://evil.test', body: validBody }),
      makeEnv(),
    );
    expect(res.status).toBe(403);
    expect(await res.json()).toEqual({ error: 'origin_not_allowed' });
  });

  it('POST with non-JSON body returns 400 invalid_body (not json)', async () => {
    const res = await handler.fetch(
      buildRequest({ method: 'POST', origin: ALLOWED, bodyText: 'not-json' }),
      makeEnv(),
    );
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: 'invalid_body', detail: 'not json' });
  });

  it('POST missing required fields returns 400 invalid_body (missing required fields)', async () => {
    const res = await handler.fetch(
      buildRequest({ method: 'POST', origin: ALLOWED, body: { model: 'x' } }),
      makeEnv(),
    );
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: 'invalid_body', detail: 'missing required fields' });
  });

  it('per-minute limit returns 429 with reason per_minute', async () => {
    const minute = Math.floor(Date.now() / 60_000);
    const kv = makeKV({ [`rl:1.2.3.4:${minute}`]: '20' });
    const res = await handler.fetch(
      buildRequest({ method: 'POST', origin: ALLOWED, body: validBody }),
      makeEnv({ RATE_LIMIT_KV: kv }),
    );
    expect(res.status).toBe(429);
    expect(await res.json()).toEqual({ error: 'rate_limited', detail: 'per_minute' });
  });

  it('daily ceiling returns 429 with reason daily_ceiling', async () => {
    const today = new Date().toISOString().slice(0, 10);
    const kv = makeKV({ [`cost:${today}`]: '10000' });
    const res = await handler.fetch(
      buildRequest({ method: 'POST', origin: ALLOWED, body: validBody }),
      makeEnv({ RATE_LIMIT_KV: kv }),
    );
    expect(res.status).toBe(429);
    expect(await res.json()).toEqual({ error: 'rate_limited', detail: 'daily_ceiling' });
  });

  it('valid request forwards to upstream and merges CORS headers', async () => {
    const upstreamBody = { id: 'msg_x', content: [{ type: 'text', text: 'ok' }] };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(upstreamBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const env = makeEnv();
    const res = await handler.fetch(
      buildRequest({ method: 'POST', origin: ALLOWED, body: validBody }),
      env,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe(env.ANTHROPIC_API_URL);
    expect((init as RequestInit).method).toBe('POST');
    const sentHeaders = (init as RequestInit).headers as Record<string, string>;
    expect(sentHeaders['Authorization']).toBe('Bearer sk-test');
    expect(sentHeaders['anthropic-version']).toBe('2023-06-01');

    expect(res.status).toBe(200);
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe(ALLOWED);
    expect(await res.json()).toEqual(upstreamBody);
  });

  it('LLM_AUTH_STYLE=x-api-key sends x-api-key header instead of Authorization Bearer', async () => {
    const upstreamBody = { id: 'msg_x', content: [{ type: 'text', text: 'ok' }] };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(upstreamBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const env = makeEnv({ LLM_AUTH_STYLE: 'x-api-key' });
    const res = await handler.fetch(
      buildRequest({ method: 'POST', origin: ALLOWED, body: validBody }),
      env,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    const sentHeaders = (init as RequestInit).headers as Record<string, string>;
    expect(sentHeaders['x-api-key']).toBe('sk-test');
    expect(sentHeaders['Authorization']).toBeUndefined();
    expect(res.status).toBe(200);
  });

  it('stream:true passes Content-Type text/event-stream through', async () => {
    const sseChunk = 'event: message_start\ndata: {}\n\n';
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(sseChunk, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );

    const res = await handler.fetch(
      buildRequest({
        method: 'POST',
        origin: ALLOWED,
        body: { ...validBody, stream: true },
      }),
      makeEnv(),
    );

    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('text/event-stream');
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    expect(await res.text()).toBe(sseChunk);
  });
});
