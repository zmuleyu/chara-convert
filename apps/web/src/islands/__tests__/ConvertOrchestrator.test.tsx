import { render, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ConvertOrchestrator from '../ConvertOrchestrator';
import { api } from '~/lib/api';
import { useStore } from '~/lib/store';

describe('ConvertOrchestrator', () => {
  it('calls api.convert when sourceCard and targetSlug present', async () => {
    useStore.getState().reset();
    const spy = vi.spyOn(api, 'convert').mockResolvedValue({
      converted: { name: 'Aerin' },
      gap: { ready_score: 1, fields: { name: 'ok' } },
    });
    render(<ConvertOrchestrator />);
    useStore.getState().setCard({ name: 'Aerin' });
    useStore.getState().setTarget('fictionlab');
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(useStore.getState().converted?.name).toBe('Aerin');
    expect(useStore.getState().gap?.ready_score).toBe(1);
  });
});
