import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PlatformBadge from '../PlatformBadge';
import { api } from '~/lib/api';
import { useStore } from '~/lib/store';

describe('PlatformBadge', () => {
  it('renders fetched targets and switches target on selection', async () => {
    useStore.getState().reset();
    vi.spyOn(api, 'platforms').mockResolvedValue({
      sources: [],
      targets: [
        { slug: 'fictionlab', name: 'FictionLab' },
        { slug: 'nomi', name: 'Nomi' },
      ],
    });
    render(<PlatformBadge />);
    await screen.findByText(/FictionLab/);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'nomi' } });
    expect(useStore.getState().targetSlug).toBe('nomi');
  });
});
