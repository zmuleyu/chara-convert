import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import HeroDemo from '../HeroDemo';

describe('HeroDemo', () => {
  it('renders the call-to-action label', () => {
    render(<HeroDemo />);
    expect(screen.getByRole('button', { name: /watch 30s demo/i })).toBeInTheDocument();
  });
});
