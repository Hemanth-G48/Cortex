import { useState, type FormEvent } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';

interface UnitFormProps {
  subjectId: number;
  onCreated: () => void;
}

/** Create a unit under a subject (plan Phase 75). */
export const UnitForm = ({ subjectId, onCreated }: UnitFormProps) => {
  const { toast } = useToast();
  const [unitNumber, setUnitNumber] = useState(1);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast('Unit name is required', 'warning');
      return;
    }
    setSaving(true);
    try {
      await endpoints.admin.createUnit(subjectId, {
        unit_number: unitNumber,
        name: name.trim(),
        description: description.trim() || null,
      });
      toast('Unit created', 'success');
      setName('');
      setDescription('');
      onCreated();
    } catch {
      toast('Could not create unit', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card" onSubmit={(e) => void submit(e)} style={{ display: 'grid', gap: '0.75rem' }}>
      <h3 style={{ fontSize: '0.9rem', marginBottom: 0 }}>Add unit</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '0.75rem' }}>
        <label style={{ display: 'grid', gap: '0.3rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Number</span>
          <input type="number" min={1} value={unitNumber} onChange={(e) => setUnitNumber(Number(e.target.value))} aria-label="Unit number" />
        </label>
        <label style={{ display: 'grid', gap: '0.3rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Arrays & Linked Lists" aria-label="Unit name" required />
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
