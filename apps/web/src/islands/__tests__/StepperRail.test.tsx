import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StepperRail from '../StepperRail';
import { useStore } from '~/lib/store';

describe('StepperRail', () => {
  it('shows 5 steps; marks "source" done when sourceCard present', () => {
    useStore.getState().reset();
    useStore.getState().setCard({ name: 'Aerin' });
    render(<StepperRail />);
    for (const label of ['Source', 'Gap', 'Convert', 'Edit', 'Export']) {
      expect(screen.getByText(new RegExp(label))).toBeInTheDocument();
    }
    // Verify Source step is marked done via data-status on parent <li>
    const sourceLink = screen.getByText(/Source/);
    const sourceLi = sourceLink.closest('li');
    expect(sourceLi).toHaveAttribute('data-status', 'done');
  });
});
