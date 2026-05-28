import type { Card, GapReport, PlatformsResponse } from './types';

const BASE = (import.meta.env.PUBLIC_API_BASE as string | undefined) ?? 'http://localhost:8000';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  platforms: () => req<PlatformsResponse>('/api/platforms', { method: 'GET' }),
  parse: (b: { raw: string }) =>
    req<{ card: Card; detectedPlatform: string | null; confidence: number }>(
      '/api/parse',
      { method: 'POST', body: JSON.stringify({ raw: b.raw, kind: 'paste' }) }
    ),
  parseFile: async (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${BASE}/api/parse`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(`${res.status} /api/parse`);
    return res.json() as Promise<{ card: Card; detectedPlatform: string | null; confidence: number }>;
  },
  convert: (b: { card: Card; targetSlug: string }) =>
    req<{ converted: Card; gap: GapReport }>('/api/convert', {
      method: 'POST',
      body: JSON.stringify(b),
    }),
};
