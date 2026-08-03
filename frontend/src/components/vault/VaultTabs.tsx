import { useRef } from 'react';

interface VaultTabsProps {
  tabs: string[];
  active: string;
  onChange: (tab: string) => void;
  /** aria-label for the tablist (defaults to 'Vault tasks'). */
  label?: string;
}

/**
 * Minimal text-based tab bar; the active tab is highlighted.
 * Keyboard accessible: Left/Right/Home/End move between tabs (Phase 90).
 */
export const VaultTabs = ({ tabs, active, onChange, label = 'Vault tasks' }: VaultTabsProps) => {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, tab: string) => {
    const idx = tabs.indexOf(tab);
    let next = -1;
    if (e.key === 'ArrowRight') next = (idx + 1) % tabs.length;
    else if (e.key === 'ArrowLeft') next = (idx - 1 + tabs.length) % tabs.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = tabs.length - 1;
    if (next !== -1) {
      e.preventDefault();
      const target = tabs[next];
      onChange(target);
      refs.current[target]?.focus();
    }
  };

  return (
    <div
      role="tablist"
      aria-label={label}
      style={{ display: 'flex', gap: 20, borderBottom: '1px solid var(--vault-border)', paddingBottom: 8, overflowX: 'auto' }}
    >
      {tabs.map((tab) => {
        const isActive = tab === active;
        return (
          <button
            key={tab}
            ref={(el) => { refs.current[tab] = el; }}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab)}
            onKeyDown={(e) => onKeyDown(e, tab)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px 2px',
              fontSize: 14,
              fontWeight: isActive ? 700 : 500,
              color: isActive ? 'var(--vault-text-primary)' : 'var(--vault-text-muted)',
              borderBottom: isActive ? '2px solid var(--habit-blue)' : '2px solid transparent',
              marginBottom: -9,
              whiteSpace: 'nowrap',
            }}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
};
