import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ExportBar from '../ExportBar';
import { useStore } from '~/lib/store';

describe('ExportBar', () => {
  it('copy-all writes full markdown to clipboard', async () => {
    useStore.getState().reset();
    useStore.getState().setConverted({ name: 'Aerin', scenario: 'Peaks' });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(<ExportBar />);
    fireEvent.click(screen.getByRole('button', { name: /copy all/i }));
    expect(writeText).toHaveBeenCalled();
    const written = writeText.mock.calls[0][0] as string;
    expect(written).toContain('Aerin');
    expect(written).toContain('Peaks');
  });

  it('PNG export button is disabled with v1 tooltip', () => {
    useStore.getState().reset();
    useStore.getState().setConverted({ name: 'Aerin' });
    render(<ExportBar />);
    const btn = screen.getByRole('button', { name: /tavern png/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', expect.stringMatching(/October 2026/i));
  });
});
