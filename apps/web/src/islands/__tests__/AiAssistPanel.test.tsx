import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AiAssistPanel from '../AiAssistPanel';
import { useStore } from '~/lib/store';

function billingResponse(body: unknown = { tier: 'free', aiUsed: 0, aiCap: 5 }): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

function sseResponse(): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(ctl) {
      ctl.enqueue(encoder.encode('data: calm \n\n'));
      ctl.enqueue(encoder.encode('data: observant\n\n'));
      ctl.close();
    },
  });
  return new Response(stream, { status: 200 });
}

function urlMockedFetch(billing: Response, sse: Response) {
  return vi.fn().mockImplementation((url: string) => {
    if (typeof url === 'string' && url.includes('/api/billing/quota')) {
      return Promise.resolve(billing);
    }
    return Promise.resolve(sse);
  });
}

describe('AiAssistPanel', () => {
  it('streams tokens via SSE and accept writes override', async () => {
    useStore.getState().reset();
    useStore.getState().setCard({ name: 'Aerin' });
    vi.stubGlobal('fetch', urlMockedFetch(billingResponse(), sseResponse()));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/calm/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /accept/i }));
    expect(useStore.getState().overrides.personality).toMatch(/calm/);
  });

  it('Reject closes without writing override', () => {
    useStore.getState().reset();
    vi.stubGlobal('fetch', urlMockedFetch(billingResponse(), sseResponse()));
    const onClose = vi.fn();
    render(<AiAssistPanel field="personality" onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /reject/i }));
    expect(onClose).toHaveBeenCalled();
    expect(useStore.getState().overrides.personality).toBeUndefined();
  });

  it('disables Generate when free quota exhausted', async () => {
    useStore.getState().reset();
    vi.stubGlobal(
      'fetch',
      urlMockedFetch(billingResponse({ tier: 'free', aiUsed: 5, aiCap: 5 }), sseResponse()),
    );
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /quota reached/i })).toBeDisabled(),
    );
  });
});
