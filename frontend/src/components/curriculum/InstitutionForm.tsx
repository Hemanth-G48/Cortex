import { useState, type FormEvent } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';

interface InstitutionFormProps {
  onCreated: () => void;
}

/** Create-institution form (plan Phase 74). */
export const InstitutionForm = ({ onCreated }: InstitutionFormProps) => {
  const { toast } = useToast();
  const [name, setName] = useState('');
  const [shortName, setShortName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !shortName.trim()) {
      toast('Name and short name are required', 'warning');
      return;
    }
    setSaving(true);
    try {
      await endpoints.admin.createInstitution({
        name: name.trim(),
        short_name: shortName.trim(),
        description: description.trim() || null,
      });
      toast('Institution created', 'success');
      setName('');
      setShortName('');
      setDescription('');
      onCreated();
    } catch {
      toast('Could not create institution', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card" onSubmit={(e) => void submit(e)} style={{ display: 'grid', gap: '0.75rem' }}>
      <h3 style={{ fontSize: '0.9rem', marginBottom: 0 }}>Add institution</h3>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. National University of Science" aria-label="Institution name" required />
      </label>
      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Short name</span>
        <input value={shortName} onChange={(e) => setShortName(e.target.value)} placeholder="e.g. NUS" aria-label="Short name" required />
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
