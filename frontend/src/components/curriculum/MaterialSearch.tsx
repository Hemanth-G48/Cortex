import { useEffect, useRef, useState } from 'react';

interface MaterialSearchProps {
  value: string;
  onChange: (q: string) => void;
}

/** Debounced search box for the material library (plan Phase 62). */
export const MaterialSearch = ({ value, onChange }: MaterialSearchProps) => {
  const [draft, setDraft] = useState(value);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      if (draft !== value) onChange(draft.trim());
    }, 300);
    return () => window.clearTimeout(timer.current);
  }, [draft, onChange, value]);

  return (
    <div style={{ position: 'relative' }}>
      <input
        type="search"
        aria-label="Search materials"
        placeholder="Search materials…"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        style={{ paddingRight: '2rem' }}
      />
      {draft && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => {
            setDraft('');
            onChange('');
          }}
          style={{
            position: 'absolute',
            right: '0.5rem',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
};
