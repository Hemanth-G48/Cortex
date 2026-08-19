import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';

/**
 * Regression tests for the request() error path: the helper must surface the
 * backend's real `detail` (FastAPI-style) instead of the generic statusText —
 * e.g. "API 400: Invalid email or password" rather than "API 400: Bad Request".
 */
describe('api request error detail surfacing', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function mockFetchOnce(status: number, body: unknown): void {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(body), {
          status,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
  }

  it('surfaces the backend detail for a 400 error', async () => {
    mockFetchOnce(400, { detail: 'Invalid email or password' });
    await expect(api.get('/kb/learning-plans/session')).rejects.toThrow(
      'API 400: Invalid email or password'
    );
  });

  it('handles FastAPI validation-error arrays (detail[].msg)', async () => {
    mockFetchOnce(422, { detail: [{ loc: ['body', 'email'], msg: 'field required' }] });
    await expect(api.post('/kb/learning-plans/session/login', {})).rejects.toThrow(
      'API 422: field required'
    );
  });

  it('falls back to the `error` key when `detail` is absent', async () => {
    mockFetchOnce(500, { error: 'boom' });
    await expect(api.put('/x', {})).rejects.toThrow('API 500: boom');
  });

  it('falls back to statusText for non-JSON error bodies', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('gateway error', { status: 502, statusText: 'Bad Gateway' }))
    );
    await expect(api.get('/x')).rejects.toThrow('API 502: Bad Gateway');
  });
});
