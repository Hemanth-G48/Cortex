import { useEffect, useState } from 'react';
import { VaultHeader } from '../components/vault';
import { endpoints, type DatabaseCounts } from '../services/api';

/** Vault Database page (Phase 57 stub — fleshed out in Phase 79). */
export const VaultDatabase = () => {
  const [counts, setCounts] = useState<DatabaseCounts | null>(null);

  useEffect(() => {
    endpoints.vault.database().then(setCounts).catch(() => {});
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}>
      <VaultHeader title="Database" />
      <div style={{ padding: 16 }}>
        {!counts && <div className="vault-muted">Loading…</div>}
        {counts && (
          <div className="vault-grid">
            {Object.entries(counts).map(([table, count]) => (
              <div key={table} className="vault-card">
                <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>{table}</div>
                <div className="vault-title" style={{ fontSize: 32 }}>{count}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
