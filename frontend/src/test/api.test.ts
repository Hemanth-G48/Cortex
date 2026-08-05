import { describe, it, expect, vi, beforeEach } from 'vitest';
import { authApi, uploadApi, setToken, clearToken, getToken } from '../services/api';

describe('api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    clearToken();
  });

  describe('authApi.login', () => {
    it('posts to /api/auth/login with identifier and password', async () => {
      const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ user: { id: 1, name: 'Alex', role: 'student' }, token: 'tok123' }),
      } as unknown as Response);

      const result = await authApi.login({ identifier: 'alex@test.com', password: 'pass' });

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ identifier: 'alex@test.com', password: 'pass' }),
      }));
      expect(result.token).toBe('tok123');
      expect(result.user.name).toBe('Alex');
    });

    it('stores token in localStorage after login', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ user: { id: 1, name: 'Alex', role: 'student' }, token: 'tok123' }),
      } as unknown as Response);

      await authApi.login({ identifier: 'a', password: 'p' });
      expect(getToken()).toBe('tok123');
    });

    it('posts to /api/auth/login with empty body for legacy login', async () => {
      const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ user: { id: 1, name: 'Alex', role: 'student', token: 'tok123' } }),
      } as unknown as Response);

      await authApi.login();

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
        method: 'POST',
        body: undefined,
      }));
    });
  });

  describe('uploadApi.upload', () => {
    it('posts FormData to /api/uploads', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ url: 'https://cdn.example.com/file.png', filename: 'file.png', size: 100, content_type: 'image/png' }),
      } as unknown as Response);

      const file = new File(['content'], 'file.png', { type: 'image/png' });
      await uploadApi.upload(file, 'avatar');

      const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const body = call[1] as RequestInit;
      const formData = body.body as FormData;
      expect(formData.get('file')).toBeInstanceOf(File);
      expect(formData.get('kind')).toBe('avatar');
    });

    it('does not include kind when not provided', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ url: 'https://cdn.example.com/file.txt', filename: 'file.txt', size: 50, content_type: 'text/plain' }),
      } as unknown as Response);

      const file = new File(['content'], 'file.txt');
      await uploadApi.upload(file);

      const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const body = call[1] as RequestInit;
      const formData = body.body as FormData;
      expect(formData.get('kind')).toBeNull();
    });
  });

  describe('auth header', () => {
    it('attaches Authorization header when token is set', async () => {
      setToken('mytoken');
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ user: { id: 1, name: 'Alex', role: 'student', token: 'mytoken' } }),
      } as unknown as Response);

      await authApi.me();

      const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const headers = (call[1] as RequestInit).headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer mytoken');
    });

    it('does not attach Authorization header when no token is set', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ user: { id: 1, name: 'Alex', role: 'student', token: 'tok' } }),
      } as unknown as Response);

      await authApi.me();

      const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const headers = (call[1] as RequestInit).headers as Record<string, string>;
      expect(headers['Authorization']).toBeUndefined();
    });
  });
});