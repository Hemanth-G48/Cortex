import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useVaultStatus } from '../../hooks/useVaultStatus';

interface EmptyStateProps {
  icon?: string;
  title?: string;
  message?: string;
  action?: ReactNode;
  /**
   * When the Second Brain has zero documents, append the vault-empty CTA
   * pointing at `second_brain/notes` (audit defect #99). Defaults to `true`;
   * pass `false` on views that don't read the vault.
   */
  vaultAware?: boolean;
  /**
   * Provide the failing request's retry handler and the state will also render
   * a Retry button plus a link to the vault job queue, so an API error is
   * never a dead end (audit defect #99).
   */
  onRetry?: () => void;
}

/**
 * Shared empty/error state. Styling is unchanged (`empty-state` + children);
 * the content becomes vault-aware: an empty vault suggests adding notes to
 * `second_brain/notes`, and a failed fetch offers retry + the job queue.
 */
export const EmptyState = ({
  icon = '📭',
  title = 'Nothing here yet',
  message = 'Data will appear here once you start adding it.',
  action,
  vaultAware = true,
  onRetry,
}: EmptyStateProps) => {
  const { documentCount, error: vaultError } = useVaultStatus();
  const vaultEmpty = vaultAware && documentCount === 0;
  const apiFailed = onRetry !== undefined || (vaultAware && vaultError);

  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title">{title}</div>
      <div className="empty-message">{message}</div>

      {vaultEmpty && (
        <div className="empty-message">
          Vault empty — add notes to <code>second_brain/notes</code> to populate this view.{' '}
          <Link to="/knowledge-base">Open Knowledge Base</Link>
        </div>
      )}

      {apiFailed && (
        <div className="empty-action" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
          {onRetry && (
            <button type="button" className="btn btn-primary" onClick={onRetry}>
              Retry
            </button>
          )}
          <Link className="btn btn-ghost" to="/knowledge-base">
            View vault jobs
          </Link>
        </div>
      )}

      {action && <div className="empty-action">{action}</div>}
    </div>
  );
};
