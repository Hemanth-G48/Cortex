import { describe, it, expect, vi, afterEach } from 'vitest';
import { confirmDelete } from './confirm';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('confirmDelete', () => {
  it('returns true and asks the standard question when confirmed', () => {
    const spy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    expect(confirmDelete('this task')).toBe(true);
    expect(spy).toHaveBeenCalledWith('Delete this task? This cannot be undone.');
  });

  it('returns false when declined without attempting anything else', () => {
    const spy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    expect(confirmDelete('this note')).toBe(false);
    expect(spy).toHaveBeenCalledOnce();
  });
});
