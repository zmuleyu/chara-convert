declare module 'cloudflare:test' {
  interface ProvidedEnv {
    CREDIT_DB: D1Database;
    RATE_LIMIT_KV: KVNamespace;
    CREDIT_DO: DurableObjectNamespace;
  }
}
