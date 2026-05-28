import {
  checkAndIncrementRateLimit,
  clientIp,
  corsHeaders,
  forwardToAnthropic,
  isOriginAllowed,
  jsonError,
  validateAnthropicBody,
  type ProxyEnv,
} from './llm-proxy';

export default {
  async fetch(request: Request, env: ProxyEnv): Promise<Response> {
    const origin = request.headers.get('Origin');

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin, env) });
    }

    if (request.method !== 'POST') {
      return jsonError(405, { error: 'method_not_allowed' }, origin, env);
    }

    if (!isOriginAllowed(origin, env)) {
      return jsonError(403, { error: 'origin_not_allowed' }, origin, env);
    }

    const gate = await checkAndIncrementRateLimit(clientIp(request), env);
    if (!gate.ok) {
      return jsonError(429, { error: 'rate_limited', detail: gate.reason }, origin, env);
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return jsonError(400, { error: 'invalid_body', detail: 'not json' }, origin, env);
    }

    if (!validateAnthropicBody(body)) {
      return jsonError(
        400,
        { error: 'invalid_body', detail: 'missing required fields' },
        origin,
        env,
      );
    }

    try {
      const upstream = await forwardToAnthropic(body, env);
      const merged = new Headers(upstream.headers);
      for (const [k, v] of Object.entries(corsHeaders(origin, env))) {
        merged.set(k, v as string);
      }
      return new Response(upstream.body, { status: upstream.status, headers: merged });
    } catch (err) {
      return jsonError(
        500,
        { error: 'upstream_failed', detail: err instanceof Error ? err.message : 'unknown' },
        origin,
        env,
      );
    }
  },
};
