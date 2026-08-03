import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: string;
  title?: string;
  message?: string;
  action?: ReactNode;
}

export const EmptyState = ({
  icon = '📭',
  title = 'Nothing here yet',
  message = 'Data will appear here once you start adding it.',
  action,
}: EmptyStateProps) => (
  <div className="empty-state">
    <div className="empty-icon">{icon}</div>
    <div className="empty-title">{title}</div>
    <div className="empty-message">{message}</div>
    {action && <div className="empty-action">{action}</div>}
  </div>
);
