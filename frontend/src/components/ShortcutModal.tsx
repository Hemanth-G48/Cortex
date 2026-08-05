import { useEffect } from 'react';
import { GLOBAL_SHORTCUTS, SHORTCUTS } from '../hooks/useKeyboardShortcuts';

interface Props {
  open: boolean;
  onClose: () => void;
}

export const ShortcutModal = ({ open, onClose }: Props) => {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Keyboard shortcuts">
        <div className="modal-header">
          <h3>
            <span className="emoji">⌨️</span> Keyboard Shortcuts
          </h3>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="modal-body">
          <p className="shortcut-section-label">NAVIGATION — press g, then a letter</p>
          <div className="shortcut-grid">
            {SHORTCUTS.map(({ key, label }) => (
              <ShortcutRow key={key} keyStr={key} label={label} />
            ))}
          </div>

          <p className="shortcut-section-label">GLOBAL</p>
          <div className="shortcut-grid">
            {GLOBAL_SHORTCUTS.map(({ key, label }) => (
              <ShortcutRow key={key} keyStr={key} label={label} />
            ))}
          </div>
        </div>
        <div className="modal-footer">Press Esc or click outside to close</div>
      </div>
    </div>
  );
};

function ShortcutRow({ keyStr, label }: { keyStr: string; label: string }) {
  const keys = keyStr.split('+');
  return (
    <div className="shortcut-row">
      <span className="shortcut-label">{label}</span>
      <div className="shortcut-keys">
        {keys.map((k, i) => (
          <kbd key={i}>{k}</kbd>
        ))}
      </div>
    </div>
  );
}
