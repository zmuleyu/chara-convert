import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import GapDashboard from '../GapDashboard';
import { useStore } from '~/lib/store';

describe('GapDashboard', () => {
  it('renders ring score and field buckets from store.gap', () => {
    useStore.getState().reset();
    useStore.getState().setGap({
      ready_score: 66,
      fields: { name: 'ok', scenario: 'missing', personality: 'partial', mes_example: 'warn' },
    });
    render(<GapDashboard />);
    expect(screen.getByText(/66%/)).toBeInTheDocument();
    expect(screen.getByText(/scenario/)).toBeInTheDocument();
    expect(screen.getByText(/missing/i)).toBeInTheDocument();
  });
});
