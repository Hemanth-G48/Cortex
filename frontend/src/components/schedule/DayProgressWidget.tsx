import { useState, useEffect, useCallback } from 'react';
import { dailyScheduleApi, type DailyScheduleStats } from '../../services/api';

interface DayProgressWidgetProps {
  className?: string;
}

export const DayProgressWidget = ({ className = '' }: DayProgressWidgetProps) => {
  const today = new Date().toISOString().slice(0, 10);
  const [stats, setStats] = useState<DailyScheduleStats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await dailyScheduleApi.stats(today);
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className={`card ${className}`.trim()}>
        <div className="card-header">Today's Progress</div>
        <div className="skeleton" style={{ height: 8, width: '60%', borderRadius: 'var(--radius)' }} />
      </div>
    );
  }

  if (!stats || stats.total === 0) {
    return (
      <div className={`card ${className}`.trim()}>
        <div className="card-header">Today's Progress</div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', padding: '0.5rem 0' }}>
          No blocks scheduled
        </div>
      </div>
    );
  }

  const pct = stats.ratio;

  return (
    <div className={`card ${className}`.trim()}>
      <div className="card-header">Today's Progress</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{ flex: 1, height: 8, background: 'var(--bg-hover)', borderRadius: 4, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${pct * 100}%`,
              background: pct === 1 ? 'var(--success)' : 'var(--info)',
              borderRadius: 4,
              transition: 'width 0.3s ease',
            }}
          />
        </div>
        <span style={{ fontSize: '0.8rem', fontWeight: 700, minWidth: 45, textAlign: 'right' }}>
          {Math.round(pct * 100)}%
        </span>
      </div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
        {stats.done} / {stats.total} done
      </div>
    </div>
  );
};
