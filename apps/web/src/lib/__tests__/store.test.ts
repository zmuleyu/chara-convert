import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';

describe('store', () => {
  beforeEach(() => useStore.getState().reset());

  it('setCard replaces sourceCard and resets overrides', () => {
    useStore.getState().setOverride('name', 'X');
    useStore.getState().setCard({ name: 'Aerin' });
    expect(useStore.getState().sourceCard?.name).toBe('Aerin');
    expect(useStore.getState().overrides).toEqual({});
  });

  it('setOverride merges per field', () => {
    useStore.getState().setOverride('name', 'Aerin');
    useStore.getState().setOverride('scenario', 'Peaks');
    expect(useStore.getState().overrides).toEqual({ name: 'Aerin', scenario: 'Peaks' });
  });

  it('finalFields merges converted with overrides (override wins)', () => {
    useStore.getState().setConverted({ name: 'Aerin', scenario: 'Old' });
    useStore.getState().setOverride('scenario', 'New');
    const final = useStore.getState().finalFields();
    expect(final).toEqual({ name: 'Aerin', scenario: 'New' });
  });
});
