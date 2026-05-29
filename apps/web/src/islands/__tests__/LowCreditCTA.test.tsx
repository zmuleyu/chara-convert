import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import LowCreditCTA from '../LowCreditCTA';
import * as billing from '~/lib/billing/client';

function stubBilling(overrides: Partial<billing.BillingState> = {}) {
  vi.spyOn(billing, 'useBilling').mockReturnValue({
    balance: 0, held: 0, loaded: true, userId: 'u-1', available: true,
    ...overrides,
  });
}

describe('LowCreditCTA', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('does not render while balance is unloaded (avoid CTA flicker on first paint)', () => {
    stubBilling({ loaded: false });
    const { container } = render(<LowCreditCTA />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders top-up CTA when loaded and balance < MIN_BALANCE_TO_TRY', () => {
    stubBilling({ balance: 50 });
    render(<LowCreditCTA />);
    expect(screen.getByText(/Low credit/i)).toBeInTheDocument();
    expect(screen.getByText(/50 credit/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /top.?up/i })).toHaveAttribute(
      'href', expect.stringContaining('pricing'),
    );
  });

  it('does not render when balance is healthy', () => {
    stubBilling({ balance: 5000 });
    const { container } = render(<LowCreditCTA />);
    expect(container).toBeEmptyDOMElement();
  });

  it('does not render when userId is null (anonymous / SSR fallback)', () => {
    stubBilling({ userId: null });
    const { container } = render(<LowCreditCTA />);
    expect(container).toBeEmptyDOMElement();
  });

  it('does not render when billing worker is unavailable (legacy mode, fail-open)', () => {
    // available=false happens when the /credit/balance fetch failed —
    // pointing at "top-up" is misleading when we can't read the balance.
    stubBilling({ balance: 0, available: false });
    const { container } = render(<LowCreditCTA />);
    expect(container).toBeEmptyDOMElement();
  });
});
