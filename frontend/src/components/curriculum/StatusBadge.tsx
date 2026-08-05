interface StatusBadgeProps {
  active: boolean;
}

/** Active / Pending status badge for the catalog admin. */
export const StatusBadge = ({ active }: StatusBadgeProps) =>
  active ? (
    <span className="badge badge-success">Active</span>
  ) : (
    <span className="badge" style={{ color: 'var(--warning)', background: 'var(--warning-muted)' }}>Pending</span>
  );
