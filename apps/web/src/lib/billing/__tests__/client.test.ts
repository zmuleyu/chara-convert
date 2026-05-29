import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useBilling } from '../client';
import { TIERS } from '../tiers';

describe('useBilling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches /api/billing/quota and returns tier+counts', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tier: 'free', aiUsed: 2, aiCap: 5 }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const { result } = renderHook(() => useBilling());
    expect(result.current).toEqual({
      tier: 'free',
      aiUsed: 0,
      aiCap: TIERS.free.aiCapPerDay,
    });

    await waitFor(() => {
      expect(result.current).toEqual({
        tier: 'free',
        aiUsed: 2,
        aiCap: 5,
      });
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/billing/quota'),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('falls back to free defaults on fetch failure', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error('network error'));
    vi.stubGlobal('fetch', mockFetch);

    const { result } = renderHook(() => useBilling());
    expect(result.current).toEqual({
      tier: 'free',
      aiUsed: 0,
      aiCap: TIERS.free.aiCapPerDay,
    });

    await waitFor(() => {
      expect(result.current).toEqual({
        tier: 'free',
        aiUsed: 0,
        aiCap: TIERS.free.aiCapPerDay,
      });
    });
  });
});
