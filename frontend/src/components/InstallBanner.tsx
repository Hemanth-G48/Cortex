import { useCallback, useEffect, useState } from 'react';

/**
 * "Add to Home Screen" banner (adapted from Shiori-v1/client/src/components/
 * InstallBanner.jsx). Listens for the browser's `beforeinstallprompt` event,
 * shows a dismissible banner, and triggers the native install prompt.
 * Automatically hides when the app is already running standalone or installed.
 */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const isStandalone = () =>
  (typeof window.matchMedia === 'function' &&
    window.matchMedia('(display-mode: standalone)').matches) ||
  (navigator as unknown as { standalone?: boolean }).standalone === true;

export const InstallBanner = () => {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setDeferred(null);
      setDismissed(true);
    };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  const install = useCallback(async () => {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
    setDismissed(true);
  }, [deferred]);

  if (isStandalone() || dismissed || !deferred) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '1rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 60,
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.7rem 1rem',
        background: 'var(--bg-card)',
        border: '1px solid var(--accent)',
        borderRadius: 14,
        boxShadow: 'var(--shadow-lg)',
        maxWidth: 'min(420px, 92vw)',
      }}
    >
      <span style={{ fontSize: '1.25rem' }}>📱</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
          Install Student Life OS
        </div>
        <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
          Use it offline, right from your home screen.
        </div>
      </div>
      <button type="button" className="btn btn-primary btn-sm" onClick={() => void install()}>
        Install
      </button>
      <button
        type="button"
        aria-label="Dismiss install prompt"
        onClick={() => setDismissed(true)}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          fontSize: '0.9rem',
          lineHeight: 1,
          padding: '0.2rem',
        }}
      >
        ✕
      </button>
    </div>
  );
};
