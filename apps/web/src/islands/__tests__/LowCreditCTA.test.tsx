import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import LowCreditCTA from '../LowCreditCTA';
import * as billing from '~/lib/billing/client';

describe('LowCreditCTA', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('does not render while balance is unloaded (avoid CTA flicker on first paint)', () => {
    vi.spyOn(billing, 'useBilling').mockReturnValue({
      balance: 0, held: 0, loaded: false, userId: 'u-1',
    });
    const { container } = render(<LowCreditCTA />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders top-up CTA when loaded and balance < MIN_BALANCE_TO_TRY', () => {
    vi.spyOn(billing, 'useBilling').mockReturnValue({
      balance: 50, held: 0, loaded: true, userId: 'u-1',
    });
    render(<LowCreditCTA />);
    expect(screen.getByText(/Low credit/i)).toBeInTheDocument();
    expect(screen.getByText(/50 credit/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /top.?up/i })).toHaveAttribute(
      'href', expect.stringContaining('pricing'),
    );
  });

  it('does not render when balance is healthy', () => {
    vi.spyOn(billing, 'useBilling').mockReturnValue({
      balance: 5000, held: 0, loaded: true, userId: 'u-1',
    });
    const { container } = render(<LowCreditCTA />);
    expect(container).toBeEmptyDOMElement();
  });

  it('does not render when userId is null (anonymous / SSR fallback)', () => {
    vi.spyOn(billing, 'useBilling').mockReturnValue({
      balance: 0, held: 0, loaded: true, userId: null,
    });
    const { container } = render(<LowCreditCTA />);
    expect(container).toBeEmptyDOMElement();
  });
});
