export interface HashState {
  step?: 'source' | 'gap' | 'convert' | 'edit' | 'export';
  target?: string;
  field?: string;
}

export function parseHash(hash: string): HashState {
  if (!hash) return {};
  const raw = hash.startsWith('#') ? hash.slice(1) : hash;
  if (!raw) return {};
  const out: Record<string, string> = {};
  for (const part of raw.split('&')) {
    const [k, v] = part.split('=');
    if (k && v) out[decodeURIComponent(k)] = decodeURIComponent(v);
  }
  return out as HashState;
}

export function buildHash(s: HashState): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(s)) {
    if (v) parts.push(`${k}=${encodeURIComponent(v)}`);
  }
  return parts.length ? `#${parts.join('&')}` : '';
}
