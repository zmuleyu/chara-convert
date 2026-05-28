import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FieldCard from '../FieldCard';
import { useStore } from '~/lib/store';

describe('FieldCard', () => {
  it('shows current value and writes override on edit', () => {
    useStore.getState().reset();
    useStore.getState().setConverted({ name: 'Aerin', scenario: 'Peaks' });
    render(<FieldCard field="scenario" />);
    expect(screen.getByText('Peaks')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /edit/i }));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'New peaks' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(useStore.getState().overrides.scenario).toBe('New peaks');
  });

  it('copy button copies value to clipboard', async () => {
    useStore.getState().reset();
    useStore.getState().setConverted({ name: 'Aerin' });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(<FieldCard field="name" />);
    fireEvent.click(screen.getByRole('button', { name: /copy/i }));
    expect(writeText).toHaveBeenCalledWith('Aerin');
  });
});
