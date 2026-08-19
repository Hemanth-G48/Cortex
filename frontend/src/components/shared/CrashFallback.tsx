import type { CSSProperties } from 'react';

interface CrashFallbackProps {
  title: string;
  error: Error;
  onRetry: () => void;
}

const noticeStyle: CSSProperties = {
  display: 'flex',
  gap: '0.75rem',
  alignItems: 'center',
  flexWrap: 'wrap',
};

/**
 * Shared recovery UI for error boundaries: title + error message + Retry /
 * Reload actions. Used by the route-level boundary in App.tsx and any
 * page-specific boundary (e.g. the Learning Path Planner) that wants the
 * same look.
 */
export function CrashFallback({ title, error, onRetry }: CrashFallbackProps) {
  return (
    <div className="notice notice-error" role="alert" style={noticeStyle}>
      <strong>{title}</strong>
      <span style={{ fontSize: '0.82rem', opacity: 0.85 }}>
        {error.message || 'An unexpected error occurred.'}
      </span>
      <span style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
        <button type="button" className="btn" onClick={onRetry}>
          ↻ Retry
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => window.location.reload()}>
          Reload page
        </button>
      </span>
    </div>
  );
}
