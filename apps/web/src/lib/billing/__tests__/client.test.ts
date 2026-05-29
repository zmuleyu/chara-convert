import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useBilling } from '../client';
import { _resetUserIdForTests } from '../userId';

describe('useBilling (credit)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _resetUserIdForTests();
  });

  afterEach(() => vi.restoreAllMocks());

  it('fetches /api/billing/credit/balance with X-User-Id and reports loaded=true', async () => {
    // Seed an existing userId so the hook reads it instead of auto-generating
    localStorage.setItem('chara-convert-user-id', 'u-test');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ balance: 4500, held: 100 }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const { result } = renderHook(() => useBilling());
    expect(result.current).toMatchObject({ balance: 0, held: 0, loaded: false });

    await waitFor(() => {
      expect(result.current).toMatchObject({
        balance: 4500, held: 100, loaded: true, userId: 'u-test',
      });
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/billing/credit/balance'),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ 'X-User-Id': 'u-test' }),
      }),
    );
  });

  it('auto-generates a userId on first mount when localStorage is empty', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ balance: 0, held: 0 }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const { result } = renderHook(() => useBilling());
    await waitFor(() => expect(result.current.loaded).toBe(true));

    expect(result.current.userId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
    expect(localStorage.getItem('chara-convert-user-id')).toBe(result.current.userId);
    // Fetched once with that generated id
    const headers = (mockFetch.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers['X-User-Id']).toBe(result.current.userId);
  });

  it('falls back to balance=0/held=0/loaded=true/available=false on fetch failure', async () => {
    localStorage.setItem('chara-convert-user-id', 'u-test');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')));

    const { result } = renderHook(() => useBilling());
    await waitFor(() => expect(result.current.loaded).toBe(true));
    // available=false is the signal consumers use to fail-open the balance
    // gate (legacy mode / worker not deployed).
    expect(result.current).toMatchObject({
      balance: 0, held: 0, userId: 'u-test', available: false,
    });
  });

  it('reports available=true on a successful fetch', async () => {
    localStorage.setItem('chara-convert-user-id', 'u-test');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ balance: 100, held: 0 }),
    }));
    const { result } = renderHook(() => useBilling());
    await waitFor(() => expect(result.current.available).toBe(true));
  });
});
