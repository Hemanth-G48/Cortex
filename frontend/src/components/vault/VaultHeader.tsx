interface VaultHeaderProps {
  title?: string;
}

/** Top full-width bar with the vault app title on the far left. */
export const VaultHeader = ({ title = 'Productivity Vault' }: VaultHeaderProps) => (
  <header
    style={{
      width: '100%',
      background: 'var(--vault-bg-card)',
      borderBottom: '1px solid var(--vault-border)',
      padding: '14px 20px',
      display: 'flex',
      alignItems: 'center',
    }}
  >
    <span className="vault-title" style={{ fontSize: 22 }}>{title}</span>
  </header>
);
