import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';

/**
 * Shared vault status (audit defect #99).
 *
 * Empty states and error fallbacks across the app need to know whether the
 * Second Brain has any documents at all, so they can show the right CTA:
 * "vault empty — add notes to `second_brain/notes`" versus a plain retry.
 *
 * `GET /api/kb/stats` is cheap and identical for every caller, so the fetch is
 * de-duplicated in a module-level cache: N mounted empty states cause one
 * request, and the result is reused for the lifetime of the session.
 */

export interface VaultStatus {
  /** Documents indexed in the vault, or `null` while unknown/unavailable. */
  documentCount: number | null;
  loading: boolean;
  /** True when the stats call itself failed (backend down / not indexed yet). */
  error: boolean;
  refresh: () => void;
}

let cachedCount: number | null = null;
let inflight: Promise<number | null> | null = null;
const listeners = new Set<(count: number | null) => void>();

const notify = (count: number | null): void => {
  cachedCount = count;
  for (const fn of listeners) fn(count);
};

const loadVaultCount = (force = false): Promise<number | null> => {
  if (!force && cachedCount !== null) return Promise.resolve(cachedCount);
  if (!force && inflight) return inflight;
  inflight = endpoints.kb
    .stats()
    .then((s) => {
      const count = typeof s.document_count === 'number' ? s.document_count : null;
      notify(count);
      return count;
    })
    .catch(() => {
      notify(null);
      return null;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
};

export const useVaultStatus = (): VaultStatus => {
  const [count, setCount] = useState<number | null>(cachedCount);
  const [loading, setLoading] = useState(cachedCount === null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    const listener = (next: number | null) => {
      if (!mounted) return;
      setCount(next);
      setError(next === null);
      setLoading(false);
    };
    listeners.add(listener);
    if (cachedCount === null) {
      loadVaultCount().then((next) => {
        if (!mounted) return;
        setCount(next);
        setError(next === null);
        setLoading(false);
      });
    } else {
      setCount(cachedCount);
      setLoading(false);
      setError(false);
    }
    return () => {
      mounted = false;
      listeners.delete(listener);
    };
  }, []);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(false);
    loadVaultCount(true).then((next) => {
      setCount(next);
      setError(next === null);
      setLoading(false);
    });
  }, []);

  return { documentCount: count, loading, error, refresh };
};
