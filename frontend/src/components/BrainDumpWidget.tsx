import { useState, useEffect, useCallback, useRef } from 'react';
import { brainDumpApi } from '../services/api';

interface BrainDumpWidgetProps {
  className?: string;
}

export const BrainDumpWidget = ({ className = '' }: BrainDumpWidgetProps) => {
  const [content, setContent] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'synced' | 'error'>('idle');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  const load = useCallback(async () => {
    try {
      const res = await brainDumpApi.get();
      if (isMountedRef.current) {
        setContent(res.content ?? '');
        setStatus('synced');
      }
    } catch {
      if (isMountedRef.current) setStatus('error');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const debouncedSave = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setStatus('saving');
    timerRef.current = setTimeout(async () => {
      try {
        await brainDumpApi.save(value);
        if (isMountedRef.current) setStatus('synced');
      } catch {
        if (isMountedRef.current) setStatus('error');
      }
    }, 700);
  }, []);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const val = e.target.value;
      setContent(val);
      debouncedSave(val);
    },
    [debouncedSave],
  );

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const statusIcon = status === 'synced' ? '✅' : status === 'saving' ? '💾' : status === 'error' ? '⚠️' : '○';
  const statusLabel = status === 'synced' ? 'Synced' : status === 'saving' ? 'Saving…' : status === 'error' ? 'Error' : '';

  return (
    <div className={`card ${className}`.trim()}>
      <div className="card-header">
        <span>Brain Dump</span>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{statusIcon} {statusLabel}</span>
      </div>
      <textarea
        value={content}
        onChange={handleChange}
        placeholder="Dump your thoughts here…"
        rows={6}
        style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
        className="form-input"
      />
    </div>
  );
};
