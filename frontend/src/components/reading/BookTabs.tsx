interface BookTabsProps {
  value: 'all' | 'reading' | 'finished' | 'want';
  onChange: (v: 'all' | 'reading' | 'finished' | 'want') => void;
}

const TABS: { value: 'all' | 'reading' | 'finished' | 'want'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'reading', label: 'Reading' },
  { value: 'finished', label: 'Finished' },
  { value: 'want', label: 'Want' },
];

export const BookTabs = ({ value, onChange }: BookTabsProps) => (
  <div className="book-tabs" style={{ display: 'flex', gap: '0.35rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
    {TABS.map((t) => (
      <button
        key={t.value}
        type="button"
        onClick={() => onChange(t.value)}
        className={`btn btn-sm ${value === t.value ? 'active' : 'btn-ghost'}`}
        style={value === t.value ? { color: 'var(--info)', borderColor: 'var(--info)', background: 'var(--info-muted)' } : undefined}
      >
        {t.label}
      </button>
    ))}
  </div>
);