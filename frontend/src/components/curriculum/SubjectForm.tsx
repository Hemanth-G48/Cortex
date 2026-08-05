import { useState, type FormEvent } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';

interface SubjectFormProps {
  programId: number;
  onCreated: () => void;
}

/** Create a subject under a program (plan Phase 75). */
export const SubjectForm = ({ programId, onCreated }: SubjectFormProps) => {
  const { toast } = useToast();
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [semester, setSemester] = useState<number | null>(1);
  const [credits, setCredits] = useState(3);
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
      await endpoints.admin.createSubject(programId, {
        name: name.trim(),
        code: code.trim(),
        semester,
        credits,
        description: description.trim() || null,
      });
      toast('Subject created', 'success');
      setName('');
      setCode('');
      setDescription('');
      onCreated();
    } catch {
      toast('Could not create subject', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card" onSubmit={(e) => void submit(e)} style={{ display: 'grid', gap: '0.75rem' }}>
      <h3 style={{ fontSize: '0.9rem', marginBottom: 0 }}>Add subject</h3>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Data Structures" aria-label="Subject name" required />
      </label>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Code</span>
        <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. CS201" aria-label="Subject code" required />
      </label>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        <label style={{ display: 'grid', gap: '0.3rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Semester</span>
          <input type="number" min={1} max={16} value={semester ?? ''} onChange={(e) => setSemester(e.target.value ? Number(e.target.value) : null)} aria-label="Semester" />
        </label>
        <label style={{ display: 'grid', gap: '0.3rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Credits</span>
          <input type="number" min={1} max={12} value={credits} onChange={(e) => setCredits(Number(e.target.value))} aria-label="Credits" />
        </label>
      </div>
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
