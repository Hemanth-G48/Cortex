export const BASE = '/api';

async function _request<T>(path: string, opts?: RequestInit): Promise<T> {  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts?.headers as Record<string, string> || {}) };
  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...opts,
  });
  if (!res.ok) {
    let detail: string | null = null;
    try {
      const body = (await res.json()) as {
        detail?: unknown;
        error?: unknown;
        message?: unknown;
      };
      const raw = body?.detail ?? body?.error ?? body?.message;
      if (typeof raw === 'string') detail = raw;
      else if (Array.isArray(raw) && raw.length > 0) {
        const first = raw[0] as { msg?: string } | undefined;
        detail = first?.msg ?? JSON.stringify(raw);
      } else if (raw !== undefined && raw !== null) detail = JSON.stringify(raw);
    } catch {
      // non-JSON error body — fall back to the status text
    }
    throw new Error(detail ? `API ${res.status}: ${detail}` : `API ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

// The raw request helper, for endpoint modules (``api/endpoints/*``) that
// need more control than the ``api`` convenience object.
export const request = _request;

export const api = {
  get: <T>(path: string) => _request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    _request<T>(path, { method: 'POST', body: data !== undefined && data !== null ? JSON.stringify(data) : undefined }),
  put: <T>(path: string, data: unknown) =>
    _request<T>(path, { method: 'PUT', body: JSON.stringify(data) }),
  patch: <T>(path: string, data?: unknown) =>
    _request<T>(path, { method: 'PATCH', body: data !== undefined && data !== null ? JSON.stringify(data) : undefined }),
  del: <T>(path: string) => _request<T>(path, { method: 'DELETE' }),
};

/**
 * Download a backend file as a browser download. The application is
 * single-user and tokenless, so no Authorization header is attached.
 */
export async function downloadAsFile(url: string, filename: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
