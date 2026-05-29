import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AiAssistPanel from '../AiAssistPanel';
import { useStore } from '~/lib/store';
import { _resetUserIdForTests } from '~/lib/billing/userId';

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
  return new Response(stream, { status: 200, headers: { 'content-type': 'text/event-stream' } });
}

function urlMockedFetch(billing: Response, sse: Response) {
  return vi.fn().mockImplementation((url: string) => {
    if (typeof url === 'string' && url.includes('/api/billing/quota')) {
      return Promise.resolve(billing);
    }
    return Promise.resolve(sse);
  });
}

beforeEach(() => _resetUserIdForTests());

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

  // Phase C: BYOK user id + OR error envelope handling

  it('sends X-User-Id header on /ai/enrich (BYOK identifier)', async () => {
    useStore.getState().reset();
    const fetchMock = urlMockedFetch(billingResponse(), sseResponse());
    vi.stubGlobal('fetch', fetchMock);
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/calm/)).toBeInTheDocument());

    const enrichCall = fetchMock.mock.calls.find(
      ([url]) => typeof url === 'string' && url.includes('/api/ai/enrich'),
    );
    expect(enrichCall).toBeDefined();
    const headers = (enrichCall![1] as RequestInit).headers as Record<string, string>;
    expect(headers['X-User-Id']).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });

  it('shows insufficient_credit UI on 402 JSON envelope', async () => {
    useStore.getState().reset();
    const err = new Response(
      JSON.stringify({ code: 'insufficient_credit', message: 'balance < amount' }),
      { status: 402, headers: { 'content-type': 'application/json' } },
    );
    vi.stubGlobal('fetch', urlMockedFetch(billingResponse(), err));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/out of credits/i)).toBeInTheDocument());
    // Top-up CTA is intentionally deferred until /api/billing/checkout returns
    // 200 (Creem cutover Oct 2026); for now just verify the message renders.
  });

  it('shows service_unavailable UI on 503 JSON envelope', async () => {
    useStore.getState().reset();
    const err = new Response(
      JSON.stringify({ code: 'service_unavailable', message: 'x' }),
      { status: 503, headers: { 'content-type': 'application/json' } },
    );
    vi.stubGlobal('fetch', urlMockedFetch(billingResponse(), err));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/temporarily down/i)).toBeInTheDocument());
  });

  it('surfaces mid-stream error frame from SSE', async () => {
    useStore.getState().reset();
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(ctl) {
        ctl.enqueue(encoder.encode('data: hello \n\n'));
        ctl.enqueue(encoder.encode('data: {"event":"error","code":"or_unavailable","message":"upstream timeout"}\n\n'));
        ctl.close();
      },
    });
    const sse = new Response(stream, { status: 200, headers: { 'content-type': 'text/event-stream' } });
    vi.stubGlobal('fetch', urlMockedFetch(billingResponse(), sse));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/upstream timeout/i)).toBeInTheDocument());
  });
});
