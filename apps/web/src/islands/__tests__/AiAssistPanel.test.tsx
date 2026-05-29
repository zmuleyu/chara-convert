import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AiAssistPanel from '../AiAssistPanel';
import { useStore } from '~/lib/store';

describe('AiAssistPanel', () => {
  it('streams tokens via SSE and accept writes override', async () => {
    useStore.getState().reset();
    useStore.getState().setCard({ name: 'Aerin' });
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(ctl) {
        ctl.enqueue(encoder.encode('data: calm \n\n'));
        ctl.enqueue(encoder.encode('data: observant\n\n'));
        ctl.close();
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));
    render(<AiAssistPanel field="personality" onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /generate/i }));
    await waitFor(() => expect(screen.getByText(/calm/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /accept/i }));
    expect(useStore.getState().overrides.personality).toMatch(/calm/);
  });

  it('Reject closes without writing override', () => {
    useStore.getState().reset();
    const onClose = vi.fn();
    render(<AiAssistPanel field="personality" onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /reject/i }));
    expect(onClose).toHaveBeenCalled();
    expect(useStore.getState().overrides.personality).toBeUndefined();
  });
});
