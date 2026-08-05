import { useState, useEffect, useCallback } from 'react';
import { dailyScheduleApi, type DailyScheduleItem } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import { EmptyState } from '../shared/EmptyState';
import { SkeletonCard } from '../shared/Skeleton';
import { CategoryTag } from './CategoryTag';
import { EnergyTag } from './EnergyTag';
import { ScheduleBlockModal } from './ScheduleBlockModal';

interface DailyScheduleViewProps {
  className?: string;
}

export const DailyScheduleView = ({ className = '' }: DailyScheduleViewProps) => {
  const { } = useAuth();
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [items, setItems] = useState<DailyScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DailyScheduleItem | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const data = await dailyScheduleApi.list(date);
      setItems(data);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  const handleToggle = useCallback(
    async (item: DailyScheduleItem) => {
      try {
        const updated = await dailyScheduleApi.toggle(item.id);
        setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
      } catch {
        /* silent */
      }
    },
    [],
  );

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await dailyScheduleApi.remove(id);
        setItems((prev) => prev.filter((i) => i.id !== id));
      } catch {
        /* silent */
      }
    },
    [],
  );

  const handleSave = useCallback(
    async (data: {
      date: string;
      time_range: string;
      activity: string;
      category: 'School' | 'Study Time' | 'Break';
      location: string | null;
      energy: 'High' | 'Medium' | 'Low';
      notes: string | null;
    }) => {
      try {
        if (editing) {
          const updated = await dailyScheduleApi.update(editing.id, data);
          setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
        } else {
          const created = await dailyScheduleApi.create(data);
          setItems((prev) => [...prev, created]);
        }
        setModalOpen(false);
        setEditing(null);
      } catch {
        /* silent */
      }
    },
    [editing],
  );

  const handleOpenAdd = useCallback(() => {
    setEditing(null);
    setModalOpen(true);
  }, []);

  const handleOpenEdit = useCallback((item: DailyScheduleItem) => {
    setEditing(item);
    setModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setModalOpen(false);
    setEditing(null);
  }, []);

  return (
    <div className={`page-section ${className}`.trim()}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
        <label htmlFor="schedule-date" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Date:</label>
        <input
          id="schedule-date"
          type="date"
          value={date}
          min={today}
          onChange={(e) => setDate(e.target.value)}
          className="form-input"
          style={{ width: 'auto' }}
        />
        <button type="button" className="btn btn-primary btn-sm" onClick={handleOpenAdd}>+ Add block</button>
      </div>

      {loading ? (
        <SkeletonCard />
      ) : items.length === 0 ? (
        <EmptyState icon="📋" title="No blocks for this date" message="Add your first schedule block to get started." action={<button type="button" className="btn btn-primary btn-sm" onClick={handleOpenAdd}>+ Add block</button>} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {items.map((item) => (
            <div key={item.id} className="card" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.6rem 0.75rem' }}>
              <input
                type="checkbox"
                checked={item.done}
                onChange={() => void handleToggle(item)}
                aria-label={`Toggle ${item.activity}`}
              />
              <span style={{ fontSize: '0.8rem', fontFamily: 'monospace', minWidth: 80 }}>{item.time_range}</span>
              <span style={{ flex: 1, fontSize: '0.85rem' }}>{item.activity}</span>
              <CategoryTag category={item.category} />
              <EnergyTag energy={item.energy} />
              {item.location && <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>📍 {item.location}</span>}
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => void handleOpenEdit(item)} title="Edit">✏️</button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => void handleDelete(item.id)} title="Delete" style={{ color: 'var(--danger)' }}>🗑</button>
            </div>
          ))}
        </div>
      )}

      <ScheduleBlockModal
        open={modalOpen}
        initial={editing}
        date={date}
        onClose={handleCloseModal}
        onSave={handleSave}
      />
    </div>
  );
};
