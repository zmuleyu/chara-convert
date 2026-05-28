import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../api';

beforeEach(() => { vi.restoreAllMocks(); });

describe('api', () => {
  it('platforms() GETs /api/platforms with PUBLIC_API_BASE', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ sources: [], targets: [] }), { status: 200 })
    );
    vi.stubGlobal('fetch', fetchMock);
    await api.platforms();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/platforms$/),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('parse() POSTs raw with kind=paste', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ card: {}, detectedPlatform: 'cai', confidence: 0.9 }), { status: 200 })
    );
    vi.stubGlobal('fetch', fetchMock);
    const r = await api.parse({ raw: 'foo' });
    expect(r.detectedPlatform).toBe('cai');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/parse$/),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ raw: 'foo', kind: 'paste' }),
      })
    );
  });

  it('throws on non-2xx', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('boom', { status: 500 })));
    await expect(api.platforms()).rejects.toThrow(/500/);
  });
});
