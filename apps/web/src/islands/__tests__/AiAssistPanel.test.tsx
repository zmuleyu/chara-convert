import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AiAssistPanel from '../AiAssistPanel';
import { useStore } from '~/lib/store';
import * as billing from '~/lib/billing/client';

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

function stubBilling(overrides: Partial<billing.BillingState> = {}) {
  vi.spyOn(billing, 'useBilling').mockReturnValue({
    balance: 5000, held: 0, loaded: true, userId: 'u-test', available: true,
    ...overrides,
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  useStore.getState().reset();
});

describe('AiAssistPanel — balance gate', () => {
  it('renders Generate enabled when balance >= MIN_BALANCE_TO_TRY', () => {
    stubBilling({ balance: 5000 });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse()));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    expect(screen.getByRole('button', { name: /Generate/i })).toBeEnabled();
  });

  it('disables button + shows "Low credit" when balance < MIN_BALANCE_TO_TRY', () => {
    stubBilling({ balance: 50 });
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    const btn = screen.getByRole('button', { name: /Low credit/i });
    expect(btn).toBeDisabled();
    // LowCreditCTA banner should render alongside
    expect(screen.getByText(/Top-up your account/i)).toBeInTheDocument();
  });

  it('disables button + shows "Loading…" while balance is unloaded (no UX flicker)', () => {
    stubBilling({ balance: 0, loaded: false, available: false });
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    const btn = screen.getByRole('button', { name: /Loading…/i });
    expect(btn).toBeDisabled();
  });

  it('fails open when billing worker is unavailable (legacy mode)', () => {
    // Loaded but unavailable + balance=0 — must NOT show "Low credit".
    // Legacy LLM_ROUTER_MODE has no credit lifecycle on the server, so
    // gating the UI here would break the entire legacy E2E.
    stubBilling({ balance: 0, loaded: true, available: false });
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    expect(screen.getByRole('button', { name: /Generate/i })).toBeEnabled();
    expect(screen.queryByText(/Low credit/i)).not.toBeInTheDocument();
  });
});

describe('AiAssistPanel — streaming + accept', () => {
  it('streams tokens via SSE and accept writes override', async () => {
    stubBilling();
    useStore.getState().setCard({ name: 'Aerin' });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse()));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/calm/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /accept/i }));
    expect(useStore.getState().overrides.personality).toMatch(/calm/);
  });

  it('Reject closes without writing override', () => {
    stubBilling();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse()));
    const onClose = vi.fn();
    render(<AiAssistPanel field="personality" onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /reject/i }));
    expect(onClose).toHaveBeenCalled();
    expect(useStore.getState().overrides.personality).toBeUndefined();
  });
});

describe('AiAssistPanel — BYOK header + OR error envelope (5fad6c8 preserved)', () => {
  it('sends X-User-Id from billing.userId (not raw localStorage)', async () => {
    stubBilling({ userId: 'u-xyz' });
    const fetchMock = vi.fn().mockResolvedValue(sseResponse());
    vi.stubGlobal('fetch', fetchMock);
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/calm/)).toBeInTheDocument());

    const enrichCall = fetchMock.mock.calls.find(
      ([url]) => typeof url === 'string' && url.includes('/api/ai/enrich'),
    );
    expect(enrichCall).toBeDefined();
    const headers = (enrichCall![1] as RequestInit).headers as Record<string, string>;
    expect(headers['X-User-Id']).toBe('u-xyz');
  });

  it('shows insufficient_credit UI on 402 JSON envelope', async () => {
    stubBilling();
    const err = new Response(
      JSON.stringify({ code: 'insufficient_credit', message: 'balance < amount' }),
      { status: 402, headers: { 'content-type': 'application/json' } },
    );
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(err));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/out of credits/i)).toBeInTheDocument());
  });

  it('shows service_unavailable UI on 503 JSON envelope', async () => {
    stubBilling();
    const err = new Response(
      JSON.stringify({ code: 'service_unavailable', message: 'x' }),
      { status: 503, headers: { 'content-type': 'application/json' } },
    );
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(err));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/temporarily down/i)).toBeInTheDocument());
  });

  it('surfaces mid-stream error frame from SSE', async () => {
    stubBilling();
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(ctl) {
        ctl.enqueue(encoder.encode('data: hello \n\n'));
        ctl.enqueue(encoder.encode('data: {"event":"error","code":"or_unavailable","message":"upstream timeout"}\n\n'));
        ctl.close();
      },
    });
    const sse = new Response(stream, { status: 200, headers: { 'content-type': 'text/event-stream' } });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sse));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/upstream timeout/i)).toBeInTheDocument());
  });
});
