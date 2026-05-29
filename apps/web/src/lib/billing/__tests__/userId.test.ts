import { describe, it, expect, beforeEach } from 'vitest';
import { getOrCreateUserId, _resetUserIdForTests } from '../userId';

describe('getOrCreateUserId', () => {
  beforeEach(() => _resetUserIdForTests());

  it('generates a v4 UUID on first call and persists it', () => {
    const id = getOrCreateUserId();
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(localStorage.getItem('chara-convert-user-id')).toBe(id);
  });

  it('returns the same id on subsequent calls (stability across reloads)', () => {
    const first = getOrCreateUserId();
    const second = getOrCreateUserId();
    expect(second).toBe(first);
  });

  it('respects an existing id written by a previous session', () => {
    localStorage.setItem('chara-convert-user-id', 'pre-existing-id');
    expect(getOrCreateUserId()).toBe('pre-existing-id');
  });
});
