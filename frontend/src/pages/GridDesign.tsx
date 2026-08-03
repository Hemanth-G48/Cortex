import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { VaultHeader } from '../components/vault';
import { getGridCols, setGridCols, GRID_COLS_OPTIONS } from '../utils/vaultGrid';

/** Vault Grid Design page (Phase 78): choose dashboard grid 1/2/3/4 columns. */
export const GridDesign = () => {
  const navigate = useNavigate();
  const [cols, setCols] = useState<number>(getGridCols());

  const apply = (n: number) => {
    setCols(n);
    setGridCols(n);
    document.documentElement.style.setProperty('--vault-cols', String(n));
  };

  useEffect(() => {
    document.documentElement.style.setProperty('--vault-cols', String(getGridCols()));
    return () => { document.documentElement.style.removeProperty('--vault-cols'); };
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}>
      <VaultHeader title="Grid Design" />
      <div style={{ padding: 16 }}>
        <div className="vault-card" style={{ marginBottom: 20 }}>
          <div className="vault-heading" style={{ marginBottom: 6 }}>Dashboard Grid Columns</div>
          <div className="vault-muted">
            Choose how many columns the vault dashboard grid uses. Your choice is saved and applied across the app.
          </div>
        </div>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {GRID_COLS_OPTIONS.map((n) => {
            const active = cols === n;
            return (
              <button
                key={n}
                onClick={() => apply(n)}
                aria-pressed={active}
                className="vault-card"
                style={{
                  cursor: 'pointer',
                  width: 180,
                  textAlign: 'left',
                  color: 'var(--vault-text-primary)',
                  borderColor: active ? 'var(--success-teal)' : 'var(--vault-border)',
                  boxShadow: active ? '0 0 0 1px var(--success-teal)' : undefined,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <span className="vault-body" style={{ fontWeight: 700 }}>{n} {n === 1 ? 'column' : 'columns'}</span>
                <span
                  style={{
                    display: 'grid',
                    gridTemplateColumns: `repeat(${n}, 1fr)`,
                    gap: 4,
                    width: '100%',
                  }}
                >
                  {Array.from({ length: n * 2 }).map((_, i) => (
                    <span
                      key={i}
                      style={{
                        height: 16,
                        borderRadius: 3,
                        background: active ? 'var(--success-teal)' : 'var(--vault-border)',
                      }}
                    />
                  ))}
                </span>
                {active && (
                  <span style={{ color: 'var(--success-teal)', fontSize: 12, fontWeight: 700 }}>✓ Selected</span>
                )}
              </button>
            );
          })}
        </div>

        <div style={{ marginTop: 20 }}>
          <button className="btn-complete" onClick={() => navigate('/vault')}>Back to Vault Dashboard</button>
        </div>
      </div>
    </div>
  );
};
