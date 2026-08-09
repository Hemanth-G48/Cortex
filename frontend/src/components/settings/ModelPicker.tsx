import { useEffect, useMemo, useRef, useState } from 'react';

interface ModelPickerProps {
  /** All available model ids (e.g. the full OmniRoute catalog). */
  models: string[];
  /** Currently selected model id ('' = use backend default). */
  value: string;
  /** Label for the backend-default option (e.g. 'auto/best-free'). */
  defaultModel?: string | null;
  /** Called when the user picks a model ('' = reset to backend default). */
  onSelect: (model: string) => void;
  placeholder?: string;
}

/**
 * Searchable model dropdown (combobox) for large model catalogs.
 *
 * Looks and behaves like a classic dropdown — a field with a ▾ arrow that
 * opens a scrollable list of every model — but the input also filters the
 * list as you type, so catalogs with thousands of entries (OmniRoute exposes
 * ~1.6k models) stay usable. Keyboard: ↑/↓ to move, Enter to pick, Esc to
 * close, click outside to dismiss.
 */
export default function ModelPicker({
  models,
  value,
  defaultModel,
  onSelect,
  placeholder,
}: ModelPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(0);

  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return models;
    return models.filter((m) => m.toLowerCase().includes(q));
  }, [models, query]);

  // Row 0 is always "use backend default"; the filtered models follow.
  const visible = useMemo(() => {
    const rows: { key: string; label: string; isDefault: boolean }[] = [
      {
        key: '__default__',
        label: defaultModel ? `Use backend default (${defaultModel})` : 'Use backend default',
        isDefault: true,
      },
      ...filtered.map((m) => ({ key: m, label: m, isDefault: false })),
    ];
    return rows;
  }, [filtered, defaultModel]);

  const openDropdown = () => {
    setQuery(value); // show the current selection while browsing
    setHighlight(0);
    setOpen(true);
  };

  const closeDropdown = () => {
    setOpen(false);
    setQuery(value);
  };

  const pick = (model: string) => {
    onSelect(model);
    setOpen(false);
    setQuery(model);
  };

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    const onDocMouseDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) closeDropdown();
    };
    const onDocKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDropdown();
    };
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('keydown', onDocKey);
    return () => {
      document.removeEventListener('mousedown', onDocMouseDown);
      document.removeEventListener('keydown', onDocKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Keep the highlighted row visible while scrolling the list. Guarded for
  // test environments (jsdom does not implement scrollIntoView).
  useEffect(() => {
    if (open && listRef.current) {
      const el = listRef.current.children[highlight] as HTMLElement | undefined;
      if (el && typeof el.scrollIntoView === 'function') {
        el.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlight, open]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        e.preventDefault();
        openDropdown();
      }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, visible.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      // With no matches only the default row remains — don't let Enter
      // silently reset the override to the backend default.
      if (visible.length === 1) return;
      const row = visible[Math.min(highlight, visible.length - 1)];
      if (row) pick(row.isDefault ? '' : row.key);
    } else if (e.key === 'Tab') {
      closeDropdown();
    }
  };

  return (
    <div className="model-picker" ref={rootRef}>
      <div className="model-picker-field">
        <input
          id="ai-model"
          className="model-picker-input"
          type="text"
          value={open ? query : value}
          placeholder={placeholder}
          spellCheck={false}
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-autocomplete="list"
          aria-controls="ai-model-list"
          aria-label="Model override"
          aria-activedescendant={open ? `ai-model-option-${highlight}` : undefined}
          onFocus={() => {
            if (!open) openDropdown();
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            setHighlight(0);
            if (!open) setOpen(true);
          }}
          onKeyDown={onKeyDown}
        />
        <button
          type="button"
          className="model-picker-arrow"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={open ? 'Close model list' : 'Open model list'}
          onClick={() => (open ? closeDropdown() : openDropdown())}
        >
          ▾
        </button>
      </div>
      {open && (
        <ul className="model-picker-list" id="ai-model-list" ref={listRef} role="listbox">
          {visible.length === 1 ? (
            <li className="model-picker-empty">No model matches “{query}”</li>
          ) : (
            visible.map((row, i) => (
              <li
                key={row.key}
                id={`ai-model-option-${i}`}
                role="option"
                aria-selected={row.key === (value || '__default__')}
                className={`model-picker-option${row.isDefault ? ' model-picker-default' : ''}${
                  i === highlight ? ' highlighted' : ''
                }`}
                onMouseEnter={() => setHighlight(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(row.isDefault ? '' : row.key);
                }}
              >
                {row.label}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
