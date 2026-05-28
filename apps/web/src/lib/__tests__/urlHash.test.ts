import { describe, it, expect } from 'vitest';
import { parseHash, buildHash } from '../urlHash';

describe('urlHash', () => {
  it('parses #step=edit&target=fictionlab&field=appearance', () => {
    expect(parseHash('#step=edit&target=fictionlab&field=appearance'))
      .toEqual({ step: 'edit', target: 'fictionlab', field: 'appearance' });
  });
  it('returns empty object for empty hash', () => {
    expect(parseHash('')).toEqual({});
  });
  it('roundtrips build/parse', () => {
    const h = buildHash({ step: 'gap', target: 'nomi' });
    expect(parseHash(h)).toEqual({ step: 'gap', target: 'nomi' });
  });
});
