// DORMANT 2026-05-29: pure-credit pivot drops subscription tiers as a routing
// input. This file is intentionally retained — see
// docs/specs/2026-05-29-or-credit-router-design.md §Key trade-offs and the
// rollout plan in docs/plans/2026-05-29-or-credit-router-plan-C-rollout.md for
// the conditions under which we'd re-import these constants (Creem cutover
// 2026-10 may re-introduce subscription tiers as a credit-grant ladder).
//
export type TierId = 'free' | 'creator' | 'studio';

export interface Tier {
  id: TierId;
  name: string;
  priceUsdMonth: number;
  aiCapPerDay: number; // -1 = unlimited
  exportFormats: ('md' | 'json' | 'png' | 'tavern-png')[];
  storage: 'local' | 'cloud';
}

export const TIERS: Record<TierId, Tier> = {
  free: {
    id: 'free',
    name: 'Free',
    priceUsdMonth: 0,
    aiCapPerDay: 5,
    exportFormats: ['md'],
    storage: 'local',
  },
  creator: {
    id: 'creator',
    name: 'Creator',
    priceUsdMonth: 9,
    aiCapPerDay: 200,
    exportFormats: ['md', 'json', 'png', 'tavern-png'],
    storage: 'cloud',
  },
  studio: {
    id: 'studio',
    name: 'Studio',
    priceUsdMonth: 29,
    aiCapPerDay: -1,
    exportFormats: ['md', 'json', 'png', 'tavern-png'],
    storage: 'cloud',
  },
};
