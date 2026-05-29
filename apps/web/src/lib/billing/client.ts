import { useState, useEffect } from 'react';
import { getOrCreateUserId } from './userId';

// Credit-balance shape (Phase C). Replaces the prior tier/quota shape; the
// free-quota Worker endpoint /api/billing/quota stays alive for the existing
// IP-rate limiter but is no longer consumed by the UI.
//
// `available` is FALSE when the billing Worker is unreachable (network error,
// CORS reject, 5xx after retries). The balance gate in consumers should
// fail-open in that case — the server-side LLM_ROUTER_MODE flag is the
// source of truth for whether credits actually apply, and gating the UI on
// `balance < N` when the worker is dead would break legacy mode entirely
// (which is the e2e + dev default).
export interface BillingState {
  balance: number;
  held: number;
  loaded: boolean;
  userId: string | null;
  available: boolean;
}

const INITIAL: BillingState = { balance: 0, held: 0, loaded: false, userId: null, available: false };

export function useBilling(): BillingState {
  const [state, setState] = useState<BillingState>(INITIAL);

  useEffect(() => {
    // SSR-safe: getOrCreateUserId returns a fresh id when localStorage is
    // unavailable but never writes — only the browser persists. In tests
    // localStorage is jsdom-backed, so the generated id sticks.
    const userId = getOrCreateUserId();

    const BASE =
      (import.meta.env.PUBLIC_BILLING_BASE as string | undefined) ??
      'http://localhost:8787';

    fetch(`${BASE}/api/billing/credit/balance`, {
      method: 'GET',
      headers: { 'X-User-Id': userId },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.json() as Promise<{ balance: number; held: number }>;
      })
      .then((data) => {
        setState({ balance: data.balance, held: data.held, loaded: true, userId, available: true });
      })
      .catch(() => {
        setState({ balance: 0, held: 0, loaded: true, userId, available: false });
      });
  }, []);

  return state;
}
