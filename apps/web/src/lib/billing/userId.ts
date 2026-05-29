// Stable per-browser user id. Acts as the BYOK identifier for the OR credit
// router (Phase C): server-side credit balance and hold/debit lifecycle are
// keyed by this id; no auth backend, no email — losing the id loses the credit
// balance with it. Persisted in localStorage so the id survives reloads.
//
// Returns the existing id, or generates a fresh v4 UUID on first call.

const STORAGE_KEY = 'chara-convert-user-id';

function generate(): string {
  // crypto.randomUUID exists in all evergreen browsers; if it's missing we
  // fall back to a getRandomValues-built v4 so the id is still cryptographically
  // random rather than Math.random.
  const c: Crypto | undefined =
    typeof globalThis !== 'undefined' ? (globalThis.crypto as Crypto | undefined) : undefined;
  if (c?.randomUUID) return c.randomUUID();
  if (c?.getRandomValues) {
    const b = new Uint8Array(16);
    c.getRandomValues(b);
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    const h = Array.from(b, (n) => n.toString(16).padStart(2, '0'));
    return `${h.slice(0, 4).join('')}-${h.slice(4, 6).join('')}-${h.slice(6, 8).join('')}-${h.slice(8, 10).join('')}-${h.slice(10, 16).join('')}`;
  }
  throw new Error('no secure RNG available');
}

export function getOrCreateUserId(): string {
  if (typeof localStorage === 'undefined') {
    // SSR / non-browser: caller should only invoke this in islands
    return generate();
  }
  const cached = localStorage.getItem(STORAGE_KEY);
  if (cached) return cached;
  const fresh = generate();
  localStorage.setItem(STORAGE_KEY, fresh);
  return fresh;
}

// Test-only escape hatch; not exported through the package index.
export function _resetUserIdForTests(): void {
  if (typeof localStorage !== 'undefined') localStorage.removeItem(STORAGE_KEY);
}
