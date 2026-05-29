import { render } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import UpgradeCTA from '../UpgradeCTA';

describe('UpgradeCTA', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows when free quota exhausted', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            tier: 'free',
            aiUsed: 5,
            aiCap: 5,
          }),
      }),
    ));

    const { container } = render(<UpgradeCTA />);
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(container.textContent).toMatch(/quota reached/i);
  });

  it('renders nothing when quota remaining', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            tier: 'free',
            aiUsed: 1,
            aiCap: 5,
          }),
      }),
    ));

    const { container } = render(<UpgradeCTA />);
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(container.textContent).not.toMatch(/quota reached/i);
  });
});
