import { useState, type FormEvent } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';

interface ProgramFormProps {
  institutionId: number;
  onCreated: () => void;
}

/** Create a program under an institution (plan Phase 75). */
export const ProgramForm = ({ institutionId, onCreated }: ProgramFormProps) => {
  const { toast } = useToast();
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [duration, setDuration] = useState(8);
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !code.trim()) {
      toast('Name and code are required', 'warning');
      return;
    }
    setSaving(true);
    try {
      await endpoints.admin.createProgram(institutionId, {
        name: name.trim(),
        code: code.trim(),
        duration,
        description: description.trim() || null,
      });
      toast('Program created', 'success');
      setName('');
      setCode('');
      setDescription('');
      onCreated();
    } catch {
      toast('Could not create program', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card" onSubmit={(e) => void submit(e)} style={{ display: 'grid', gap: '0.75rem' }}>
      <h3 style={{ fontSize: '0.9rem', marginBottom: 0 }}>Add program</h3>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. B.Sc. Computer Science" aria-label="Program name" required />
      </label>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Code</span>
        <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. CS" aria-label="Program code" required />
      </label>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Duration (semesters)</span>
        <input type="number" min={1} max={16} value={duration} onChange={(e) => setDuration(Number(e.target.value))} aria-label="Duration" />
      </label>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Description (optional)</span>
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} aria-label="Description" />
      </label>
      <div>
        <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
          {saving ? 'Creating…' : '＋ Create'}
        </button>
      </div>
    </form>
  );
};
