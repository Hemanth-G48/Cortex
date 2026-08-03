interface QuickActionLinkProps {
  label: string;
  icon?: string;
  onClick: () => void;
}

/** Vault quick-action text link with a leading icon (e.g. "+", "▦", "🗄"). */
export const QuickActionLink = ({ label, icon = '+', onClick }: QuickActionLinkProps) => (
  <button
    onClick={onClick}
    style={{
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      color: 'var(--habit-blue)',
      fontSize: 13,
      fontWeight: 600,
      padding: '4px 0',
    }}
  >
    <span aria-hidden style={{ color: 'var(--vault-text-muted)', fontWeight: 700 }}>{icon}</span>
    {label}
  </button>
);
