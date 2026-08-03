interface Tab {
  id: string;
  label: string;
  count?: number;
}

interface RpgTabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const RpgTabs = ({ tabs, activeTab, onChange, className = '' }: RpgTabsProps) => {
  return (
    <div className={`rpg-tabs ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`rpg-tab ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onChange(tab.id)}
          type="button"
        >
          {tab.label}
          {tab.count !== undefined && (
            <span
              style={{
                marginLeft: '6px',
                fontSize: '0.65rem',
                color: activeTab === tab.id ? '#ff9800' : '#707070',
              }}
            >
              ({tab.count})
            </span>
          )}
        </button>
      ))}
    </div>
  );
};
