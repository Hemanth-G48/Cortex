import { useEffect, useState } from 'react';
import { EditIcon, VaultHeader } from '../components/vault';
import { useToast } from '../hooks/useToast';
import { endpoints } from '../services/api';
import type { Goal, Habit } from '../services/api';

interface GoalFormState {
  title: string;
  quarter: string;
  year: number;
  habit_id: number | null;
  target_date: string;
  progress_percentage: number;
}

const emptyForm = (): GoalFormState => ({
  title: '',
  quarter: 'Q1',
  year: new Date().getFullYear(),
  habit_id: null,
  target_date: '',
  progress_percentage: 0,
});

export const GoalsSetting = () => {
  const { toast } = useToast();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [habits, setHabits] = useState<Habit[]>([]);
  const [form, setForm] = useState<GoalFormState>(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [suggestedGoals, setSuggestedGoals] = useState<string[]>([]);

  const load = () => {
    endpoints.goals.list().then(setGoals).catch(() => setError('Failed to load goals'));
    endpoints.habits.list().then(setHabits).catch(() => {});
    // Defect #51 fix: pre-fill goal suggestions from the weekly review engine
    // so the page is not limited to direct goals/habits lists.
    endpoints.kb.weeklyReview.overview().then((wr) => {
      setSuggestedGoals(wr.derived_goals.map((g) => g.title));
    }).catch(() => setSuggestedGoals([]));
  };

  useEffect(() => { load(); }, []);

  const habitById = (id: number | null) => habits.find((h) => h.id === id);

  const submit = async () => {
    if (!form.title.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        title: form.title.trim(),
        quarter: form.quarter,
        year: form.year,
        habit_id: form.habit_id,
        target_date: form.target_date || null,
        progress_percentage: form.progress_percentage,
        is_completed: editingId != null
          ? (goals.find((g) => g.id === editingId)?.is_completed ?? false)
          : false,
      };
      if (editingId != null) {
        await endpoints.goals.update(editingId, payload);
        toast('Goal updated', 'success');
      } else {
        await endpoints.goals.create(payload);
        toast('Goal created', 'success');
      }
      setForm(emptyForm());
      setEditingId(null);
      setShowForm(false);
      load();
    } catch {
      setError('Failed to save goal');
      toast('Could not save goal', 'error');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (g: Goal) => {
    setEditingId(g.id);
    setForm({
      title: g.title,
      quarter: g.quarter,
      year: g.year,
      habit_id: g.habit_id,
      target_date: g.target_date ?? '',
      progress_percentage: g.progress_percentage,
    });
    setShowForm(true);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(emptyForm());
    setShowForm(false);
  };

  const toggleComplete = (g: Goal) => {
    endpoints.goals.complete(g.id)
      .then(() => {
        toast('Goal marked complete', 'success');
        load();
      })
      .catch(() => { setError('Failed to update goal'); toast('Could not update goal', 'error'); });
  };

  const remove = (id: number) => {
    endpoints.goals.delete(id)
      .then(() => {
        toast('Goal deleted', 'info');
        load();
      })
      .catch(() => { setError('Failed to delete goal'); toast('Could not delete goal', 'error'); });
  };

  const completedCount = goals.filter((g) => g.is_completed).length;
  const habitGoalCount = goals.filter((g) => g.habit_id != null).length;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}>
      <VaultHeader title="Goals Setting" />
      <div style={{ padding: 16 }}>

        {/* Summary strip */}
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
          <div className="vault-card" style={{ minWidth: 140 }}>
            <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Total goals</div>
            <div className="vault-title" style={{ fontSize: 28 }}>{goals.length}</div>
          </div>
          <div className="vault-card" style={{ minWidth: 140 }}>
            <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Completed</div>
            <div className="vault-title" style={{ fontSize: 28, color: 'var(--success-teal)' }}>{completedCount}</div>
          </div>
          <div className="vault-card" style={{ minWidth: 140 }}>
            <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Habit goals</div>
            <div className="vault-title" style={{ fontSize: 28, color: 'var(--habit-blue)' }}>{habitGoalCount}</div>
          </div>
        </div>

        {error && (
          <div style={{ padding: '10px 14px', marginBottom: 16, borderRadius: 6, border: '1px solid var(--habit-red)', color: 'var(--habit-red)', fontSize: 13 }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: 12 }}>
          <button className="btn-complete" onClick={() => { if (showForm) cancelEdit(); else setShowForm(true); }}>
            {showForm ? 'Cancel' : '+ New Goal'}
          </button>
        </div>

        {showForm && (
          <div className="vault-card" style={{ marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {suggestedGoals.length > 0 && (
            <div style={{ fontSize: 12, color: 'var(--vault-text-muted)', marginBottom: 8 }}>
              Suggestions from weekly review: {suggestedGoals.slice(0, 5).join(', ')}
              {suggestedGoals.length > 5 && ` +${suggestedGoals.length - 5} more`}
            </div>
          )}
          <input
              placeholder="Goal title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
            />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <select
                value={form.quarter}
                onChange={(e) => setForm({ ...form, quarter: e.target.value })}
                style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
              >
                <option>Q1</option><option>Q2</option><option>Q3</option><option>Q4</option>
              </select>
              <input
                type="number"
                value={form.year}
                onChange={(e) => setForm({ ...form, year: Number(e.target.value) || new Date().getFullYear() })}
                style={{ width: 80, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
              />
              <select
                value={form.habit_id ?? ''}
                onChange={(e) => setForm({ ...form, habit_id: e.target.value ? Number(e.target.value) : null })}
                style={{ flex: 1, minWidth: 160, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
              >
                <option value="">No linked habit</option>
                {habits.map((h) => (
                  <option key={h.id} value={h.id}>{h.name}</option>
                ))}
              </select>
              <input
                type="date"
                value={form.target_date}
                onChange={(e) => setForm({ ...form, target_date: e.target.value })}
                style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
              />
              <input
                type="number"
                min={0}
                max={100}
                value={form.progress_percentage}
                onChange={(e) => setForm({ ...form, progress_percentage: Math.min(100, Math.max(0, Number(e.target.value))) })}
                title="Progress %"
                placeholder="Progress %"
                style={{ width: 110, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
              />
            </div>
            <button className="btn-complete" onClick={submit} disabled={!form.title.trim() || saving}>
              {saving ? 'Saving…' : editingId != null ? 'Save Changes' : 'Create Goal'}
            </button>
          </div>
        )}

        {goals.length === 0 && !showForm && (
          <div className="vault-muted">No goals yet. Create your first goal above.</div>
        )}

        <div className="vault-grid">
          {goals.map((g) => {
            const habit = habitById(g.habit_id);
            return (
              <div className="vault-card" key={g.id} style={g.is_completed ? { opacity: 0.75 } : undefined}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: 8 }}>
                  <h3 style={{ fontSize: 15, textDecoration: g.is_completed ? 'line-through' : 'none', color: g.is_completed ? 'var(--vault-text-muted)' : 'var(--vault-text-primary)', marginBottom: 4 }}>
                    {g.title}
                  </h3>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <EditIcon onClick={() => startEdit(g)} title={`Edit ${g.title}`} />
                    <button
                      onClick={() => remove(g.id)}
                      title="Delete goal"
                      aria-label={`Delete ${g.title}`}
                      style={{ background: 'none', border: '1px solid var(--vault-border)', borderRadius: 6, color: 'var(--habit-red)', cursor: 'pointer', fontSize: 13, lineHeight: 1, padding: '4px 6px' }}
                    >
                      🗑
                    </button>
                  </div>
                </div>

                <div className="vault-muted" style={{ marginBottom: 8 }}>
                  {g.quarter} {g.year}
                  {g.target_date ? ` · Due ${g.target_date}` : ''}
                </div>

                {habit && (
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '2px 8px',
                      borderRadius: 999,
                      border: '1px solid var(--vault-border)',
                      fontSize: 12,
                      marginBottom: 8,
                    }}
                  >
                    <span style={{ width: 8, height: 8, borderRadius: 999, background: `var(--habit-${habit.color_theme})` }} />
                    {habit.name}
                  </div>
                )}

                <div className="xp-bar" style={{ width: '100%', height: 8, marginTop: '0.25rem' }}>
                  <div
                    className="xp-fill"
                    style={{ width: `${g.progress_percentage}%`, height: 8, background: g.is_completed ? 'var(--success-teal)' : 'var(--accent)' }}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
                  <span className="vault-muted">{g.progress_percentage}%</span>
                  <button
                    className={`btn-complete${g.is_completed ? ' done' : ''}`}
                    onClick={() => toggleComplete(g)}
                  >
                    {g.is_completed ? '✓ Done' : 'Mark Complete'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
