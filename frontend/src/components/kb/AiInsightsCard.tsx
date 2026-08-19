import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import type { AIInsightsResponse } from '../../services/api';

/**
 * Persisted AI productivity insights (Idea 95).
 *
 * The backend stores the last generated insight per user, so opening the
 * dashboard returns the saved snapshot instantly ("cached" badge + last
 * updated timestamp) with NO LLM call. The provider is only consulted on the
 * explicit ↻ Refresh click (``force``), which recomputes and re-persists.
 * The deterministic fallback keeps the card functional when AI is offline.
 */
export const AiInsightsCard = () => {
  const [data, setData] = useState<AIInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async (force = false) => {
    setLoading(true);
    setError(false);
    try {
      setData(await endpoints.ai.insights(force));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="card" style={{ position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1.15rem' }}>💡</span>
        <h3 style={{ flex: 1, margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>AI Insights</h3>
        {data?.cached && (
          <span
            className="badge"
            title="Served from the response cache — identical stats within the TTL window"
            style={{ color: 'var(--info)', background: 'var(--info-muted)' }}
          >
            cached
          </span>
        )}          {data?.ai_used === false && (
            <span className="badge" style={{ color: 'var(--warning)', background: 'var(--warning-muted)' }}>
              offline mode
            </span>
          )}
          {data?.analyzed_at && (
            <span
              className="badge"
              title="When this insight was generated (reused until you hit Refresh)"
              style={{ color: 'var(--text-secondary)', background: 'var(--bg-hover)' }}
            >
              {new Date(data.analyzed_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
            </span>
          )}
      </div>

      {loading ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Analyzing your stats…</div>
      ) : error ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--danger)' }}>
          Couldn't load insights. Check that the backend is running.
        </div>
      ) : data ? (
        <>
          <div style={{ fontSize: '0.82rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
            {data.insights}
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '0.75rem', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            <span>Tasks: {data.stats.tasks.completed}/{data.stats.tasks.total} done</span>
            <span>XP: {data.stats.user.total_xp}</span>
            <span>Streak: {data.stats.user.streak} days</span>
            <span>Habits: {data.stats.habits.active_streaks} active</span>
          </div>
          <div style={{ marginTop: '0.75rem', textAlign: 'right' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void load(true)}>
              ↻ Refresh
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
};
