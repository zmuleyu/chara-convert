import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SourcePicker from '../SourcePicker';
import { api } from '~/lib/api';
import { useStore } from '~/lib/store';

describe('SourcePicker', () => {
  it('on paste, calls api.parse and sets card+platform in store', async () => {
    useStore.getState().reset();
    vi.spyOn(api, 'parse').mockResolvedValue({
      card: { name: 'Aerin' },
      detectedPlatform: 'cai',
      confidence: 0.9,
    });
    render(<SourcePicker />);
    const ta = screen.getByPlaceholderText(/paste your character/i);
    fireEvent.change(ta, { target: { value: 'Character name: Aerin' } });
    fireEvent.click(screen.getByRole('button', { name: /detect/i }));
    await screen.findByText(/cai/i);
    expect(useStore.getState().sourceCard?.name).toBe('Aerin');
    expect(useStore.getState().detectedPlatform).toBe('cai');
  });
});
