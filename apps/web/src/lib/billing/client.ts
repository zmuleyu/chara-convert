import { useState, useEffect } from 'react';
import type { TierId } from './tiers';
import { TIERS } from './tiers';

export interface BillingState {
  tier: TierId;
  aiUsed: number;
  aiCap: number;
}

export function useBilling(): BillingState {
  const [state, setState] = useState<BillingState>({
    tier: 'free',
    aiUsed: 0,
    aiCap: TIERS.free.aiCapPerDay,
  });

  useEffect(() => {
    const BASE =
      (import.meta.env.PUBLIC_BILLING_BASE as string | undefined) ??
      'http://localhost:8787';

    fetch(`${BASE}/api/billing/quota`, { method: 'GET' })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.json();
      })
      .then((data: { tier: TierId; aiUsed: number; aiCap: number }) => {
        setState({
          tier: data.tier,
          aiUsed: data.aiUsed,
          aiCap: data.aiCap,
        });
      })
      .catch(() => {
        setState({
          tier: 'free',
          aiUsed: 0,
          aiCap: TIERS.free.aiCapPerDay,
        });
      });
  }, []);

  return state;
}
