import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { endpoints, type GlobalSearchHit } from '../../services/api';

const DOMAIN_ICONS: Record<string, string> = {
  vault: '🧠',
  materials: '📄',
  subjects: '📚',
  units: '📑',
  tasks: '✅',
  assignments: '📝',
};

const DOMAIN_LABELS: Record<string, string> = {
  vault: 'Vault',
  materials: 'Materials',
  subjects: 'Subjects',
  units: 'Units',
  tasks: 'Tasks',
  assignments: 'Assignments',
};

const DEBOUNCE_MS = 250;

export const CommandPalette = () => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [groups, setGroups] = useState<Record<string, GlobalSearchHit[]>>({});
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const closePalette = useCallback(() => setOpen(false), []);

  // Ctrl/Cmd+Shift+K toggles the palette (Ctrl+K stays with the AI chat).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((o) => {
          if (!o) window.setTimeout(() => inputRef.current?.focus(), 0);
          return !o;
        });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Debounced global search (phrase 93/97).
  useEffect(() => {
    if (!open) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setGroups({});
      setLoading(false);
      return;
    }
    setLoading(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      endpoints.search
        .global(trimmed)
        .then((res) => {
          setGroups(res.groups ?? {});
          setActive(0);
        })
        .catch(() => setGroups({}))
        .finally(() => setLoading(false));
    }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, open]);

  // Flatten hits in group order for keyboard navigation.
  const flatHits = useMemo(() => {
    const out: GlobalSearchHit[] = [];
    for (const hits of Object.values(groups)) out.push(...hits);
    return out;
  }, [groups]);

  const domainOrder = useMemo(() => {
    const order: string[] = [];
    for (const d of Object.keys(groups)) order.push(d);
    return order;
  }, [groups]);

  const goTo = (hit: GlobalSearchHit) => {
    closePalette();
    if (hit.domain === 'vault') {
      // Open the deep vault search page with the query (phrase 98).
      navigate(`/vault-search?q=${encodeURIComponent(query.trim())}`);
    } else {
      navigate(hit.url || '/');
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      closePalette();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => (flatHits.length ? (a + 1) % flatHits.length : 0));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => (flatHits.length ? (a - 1 + flatHits.length) % flatHits.length : 0));
      return;
    }
    if (e.key === 'Enter' && flatHits[active]) {
      e.preventDefault();
      goTo(flatHits[active]);
    }
  };

  if (!open) return null;

  return (
    <div
      className="modal-overlay"
      onClick={closePalette}
      style={{ zIndex: 950, alignItems: 'flex-start', paddingTop: '12vh' }}
    >
      <div
        role="dialog"
        aria-label="Global search"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
        style={{
          width: 'min(620px, calc(100vw - 2rem))',
          background: 'var(--bg-card, #181a1c)',
          border: '1px solid var(--border, #2d2d2d)',
          borderRadius: 14,
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
          overflow: 'hidden',
        }}
      >
        {/* Input */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.85rem 1rem', borderBottom: '1px solid var(--border, #2d2d2d)' }}>
          <span style={{ fontSize: '1rem' }}>🔎</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search vault, materials, tasks…  (Ctrl+Shift+K)"
            aria-label="Global search query"
            style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: '0.95rem', color: 'var(--text, #111)' }}
          />
          {loading && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>…</span>}
          <kbd style={{ fontSize: '0.62rem', opacity: 0.6 }}>esc</kbd>
        </div>

        {/* Results */}
        <div style={{ maxHeight: '52vh', overflowY: 'auto', padding: '0.5rem' }}>
          {query.trim() === '' ? (
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '1rem', textAlign: 'center' }}>
              Start typing to search across your vault, curriculum, tasks and assignments.
            </p>
          ) : flatHits.length === 0 ? (
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '1rem', textAlign: 'center' }}>
              {loading ? 'Searching…' : `No matches for “${query}”.`}
            </p>
          ) : (
            domainOrder.map((domain) => (
              <div key={domain} style={{ marginBottom: '0.35rem' }}>
                <div
                  style={{
                    fontSize: '0.62rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: 'var(--text-muted)',
                    padding: '0.4rem 0.6rem 0.2rem',
                  }}
                >
                  {DOMAIN_LABELS[domain] ?? domain} ({groups[domain].length})
                </div>
                {groups[domain].map((hit) => {
                  const idx = flatHits.indexOf(hit);
                  const isActive = idx === active;
                  return (
                    <button
                      key={`${domain}-${hit.id}`}
                      type="button"
                      onClick={() => goTo(hit)}
                      onMouseEnter={() => setActive(idx)}
                      style={{
                        display: 'flex',
                        gap: '0.6rem',
                        alignItems: 'center',
                        width: '100%',
                        textAlign: 'left',
                        padding: '0.55rem 0.7rem',
                        borderRadius: 8,
                        border: 'none',
                        background: isActive ? 'var(--accent, #2563eb)22' : 'transparent',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        color: 'var(--text, #111)',
                      }}
                    >
                      <span style={{ fontSize: '1rem' }}>{DOMAIN_ICONS[domain] ?? '•'}</span>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {hit.title}
                      </span>
                      {hit.snippet && (
                        <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', maxWidth: '40%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {hit.snippet}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div
          style={{
            padding: '0.5rem 1rem',
            borderTop: '1px solid var(--border, #2d2d2d)',
            fontSize: '0.62rem',
            color: 'var(--text-muted)',
            display: 'flex',
            gap: '1rem',
          }}
        >
          <span><kbd>↑</kbd> <kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
};
