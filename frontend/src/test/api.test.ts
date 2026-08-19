import { describe, it, expect, vi, beforeEach } from 'vitest';
import { profileApi, uploadApi } from '../services/api';

describe('api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('profileApi.get', () => {
    it('posts to /api/profile and returns the owner', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ user: { id: 1, name: 'Alex', role: 'student' } }),
      } as unknown as Response);

      const result = await profileApi.get();

      const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(call[0]).toBe('/api/profile');
      expect(result.user.name).toBe('Alex');
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

  describe('requests are tokenless', () => {
    it('never attaches an Authorization header', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ user: { id: 1, name: 'Alex' } }),
      } as unknown as Response);

      await profileApi.get();

      const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const headers = (call[1] as RequestInit).headers as Record<string, string>;
      expect(headers['Authorization']).toBeUndefined();
    });
  });
});
