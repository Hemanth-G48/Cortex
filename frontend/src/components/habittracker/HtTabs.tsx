interface HtTabDef {
  id: string;
  label: string;
  count?: number;
}

interface HtTabsProps {
  tabs: HtTabDef[];
  activeTab: string;
  onChange: (id: string) => void;
  ariaLabel?: string;
}

/** Scoped tab bar for the good/bad habit rows (Phase 71, 80). */
export const HtTabs = ({ tabs, activeTab, onChange, ariaLabel }: HtTabsProps) => (
  <div className="ht-tabs" role="tablist" aria-label={ariaLabel ?? 'Filter habits'}>
    {tabs.map((t) => (
      <button
        key={t.id}
        type="button"
        role="tab"
        aria-selected={activeTab === t.id}
        className={`ht-tab${activeTab === t.id ? ' active' : ''}`}
        onClick={() => onChange(t.id)}
      >
        {t.label}
        {t.count !== undefined && ` (${t.count})`}
      </button>
    ))}
  </div>
);
