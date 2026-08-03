import { useCallback, useEffect, useState } from 'react';
import { EditIcon, VaultHeader } from '../components/vault';
import { useToast } from '../hooks/useToast';
import { endpoints } from '../services/api';
import type { Habit, HabitLog, HabitStats } from '../services/api';

interface EditingLog {
  id: number;
  habit_id: number;
  date: string;
  count: number;
  completed: boolean;
}

export const HabitLogs = () => {
  const { toast } = useToast();
  const [habits, setHabits] = useState<Habit[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [logs, setLogs] = useState<HabitLog[]>([]);
  const [stats, setStats] = useState<HabitStats | null>(null);
  const [editing, setEditing] = useState<EditingLog | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHabits = useCallback(() => {
    endpoints.habits.list().then((h) => {
      setHabits(h);
      setSelectedId((cur) => cur ?? h[0]?.id ?? null);
    }).catch(() => setError('Failed to load habits'));
  }, []);

  useEffect(() => { loadHabits(); }, [loadHabits]);

  const loadLogs = useCallback((habitId: number) => {
    setError(null);
    endpoints.habits.logs(habitId)
      .then((l) => setLogs(l.sort((a, b) => b.date.localeCompare(a.date))))
      .catch(() => setError('Failed to load logs'));
    endpoints.habits.stats(habitId).then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedId != null) loadLogs(selectedId);
  }, [selectedId, loadLogs]);

  const selectedHabit = habits.find((h) => h.id === selectedId) ?? null;

  const saveEdit = async () => {
    if (!editing || !editing.date || saving) return;
    setSaving(true);
    setError(null);
    try {
      await endpoints.habits.updateLog(editing.id, {
        habit_id: editing.habit_id,
        date: editing.date,
        count: editing.count,
        completed: editing.completed,
      });
      setEditing(null);
      loadHabits();
      loadLogs(editing.habit_id);
      toast('Log updated', 'success');
    } catch {
      setError('Failed to update log');
      toast('Could not update log', 'error');
    } finally {
      setSaving(false);
    }
  };

  const remove = (log: HabitLog) => {
    setError(null);
    endpoints.habits.deleteLog(log.id)
      .then(() => {
        toast('Log deleted', 'info');
        loadHabits();
        if (selectedId != null) loadLogs(selectedId);
      })
      .catch(() => { setError('Failed to delete log'); toast('Could not delete log', 'error'); });
  };

  const formatDate = (iso: string) => {
    const d = new Date(`${iso}T00:00:00`);
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}>
      <VaultHeader title="Habit Logs" />
      <div style={{ padding: 16 }}>

        {error && (
          <div style={{ padding: '10px 14px', marginBottom: 16, borderRadius: 6, border: '1px solid var(--habit-red)', color: 'var(--habit-red)', fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Habit selector */}
        <div style={{ marginBottom: 16 }}>
          <label className="vault-muted" style={{ display: 'block', marginBottom: 6 }}>Habit</label>
          <select
            value={selectedId ?? ''}
            onChange={(e) => {
              setEditing(null);
              setSelectedId(e.target.value ? Number(e.target.value) : null);
            }}
            style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-card)', color: 'var(--vault-text-primary)', minWidth: 240 }}
          >
            {habits.map((h) => (
              <option key={h.id} value={h.id}>{h.name}</option>
            ))}
          </select>
        </div>

        {/* Stats strip for the selected habit */}
        {selectedHabit && stats && (
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
            <div className="vault-card" style={{ minWidth: 140 }}>
              <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Records this month</div>
              <div className="vault-title" style={{ fontSize: 28 }}>{stats.records_this_month}</div>
            </div>
            <div className="vault-card" style={{ minWidth: 140 }}>
              <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Days missed</div>
              <div className="vault-title" style={{ fontSize: 28, color: 'var(--habit-orange)' }}>{stats.days_missed}</div>
            </div>
            <div className="vault-card" style={{ minWidth: 140 }}>
              <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Current streak</div>
              <div className="vault-title" style={{ fontSize: 28, color: `var(--habit-${selectedHabit.color_theme})` }}>{selectedHabit.current_streak}d</div>
            </div>
            {stats.is_new_record && (
              <div className="vault-card" style={{ minWidth: 140, borderColor: 'var(--habit-red)' }}>
                <div className="vault-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Status</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--habit-red)' }}>🏆 New record</div>
              </div>
            )}
          </div>
        )}

        {/* Log history table */}
        <div className="vault-card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--vault-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="vault-heading" style={{ fontSize: 15 }}>
              {selectedHabit ? `Log history · ${selectedHabit.name}` : 'Log history'}
            </span>
            <span className="vault-muted">{logs.length} entries</span>
          </div>

          {logs.length === 0 && (
            <div className="vault-muted" style={{ padding: '24px 16px' }}>No logs for this habit yet.</div>
          )}

          {logs.length > 0 && (
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Count</th>
                  <th>Completed</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => {
                  const isEditingThis = editing?.id === log.id;
                  return (
                    <tr key={log.id}>
                      <td>
                        {isEditingThis ? (
                          <input
                            type="date"
                            value={editing.date}
                            onChange={(e) => setEditing({ ...editing, date: e.target.value })}
                            style={{ padding: '5px 8px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
                          />
                        ) : (
                          formatDate(log.date)
                        )}
                      </td>
                      <td>
                        {isEditingThis ? (
                          <input
                            type="number"
                            min={0}
                            value={editing.count}
                            onChange={(e) => setEditing({ ...editing, count: Math.max(0, Number(e.target.value) || 0) })}
                            style={{ width: 70, padding: '5px 8px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}
                          />
                        ) : (
                          log.count
                        )}
                      </td>
                      <td>
                        {isEditingThis ? (
                          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={editing.completed}
                              onChange={(e) => setEditing({ ...editing, completed: e.target.checked })}
                              style={{ accentColor: 'var(--success-teal)', width: 16, height: 16, cursor: 'pointer' }}
                            />
                            <span className="vault-muted">Completed</span>
                          </label>
                        ) : (
                          <span style={{ color: log.completed ? 'var(--success-teal)' : 'var(--vault-text-muted)' }}>
                            {log.completed ? '✓ Yes' : '✗ No'}
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {isEditingThis ? (
                          <>
                            <button className="btn-complete" onClick={saveEdit} disabled={saving} style={{ marginRight: 6 }}>
                              {saving ? 'Saving…' : 'Save'}
                            </button>
                            <button className="btn-complete" onClick={() => setEditing(null)}>Cancel</button>
                          </>
                        ) : (
                          <>
                            <EditIcon
                              onClick={() => setEditing({ id: log.id, habit_id: log.habit_id, date: log.date, count: log.count, completed: log.completed })}
                              title={`Edit log ${formatDate(log.date)}`}
                            />
                            <button
                              onClick={() => remove(log)}
                              title="Delete log"
                              aria-label={`Delete log ${formatDate(log.date)}`}
                              style={{ background: 'none', border: '1px solid var(--vault-border)', borderRadius: 6, color: 'var(--habit-red)', cursor: 'pointer', fontSize: 13, lineHeight: 1, padding: '4px 6px', marginLeft: 6 }}
                            >
                              🗑
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
