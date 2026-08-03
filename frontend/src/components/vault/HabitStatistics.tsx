interface HabitStat {
  habit: string;
  records_this_month: number;
  days_missed: number;
  is_new_record: boolean;
}

interface HabitStatisticsProps {
  stats: HabitStat[];
}

/** Sidebar widget: one stat card per habit (records, missed days, new-record badge). */
export const HabitStatistics = ({ stats }: HabitStatisticsProps) => (
  <div className="vault-card">
    <div className="vault-heading" style={{ marginBottom: 10 }}>Habit Statistics</div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {stats.map((s) => (
        <div key={s.habit} style={{ border: '1px solid var(--vault-border)', borderRadius: 8, padding: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <span className="vault-body" style={{ fontWeight: 600 }}>{s.habit}</span>
            {s.is_new_record && (
              <span
                style={{
                  background: 'var(--success-teal)',
                  color: '#fff',
                  borderRadius: 6,
                  padding: '1px 6px',
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                New record
              </span>
            )}
          </div>
          <div className="vault-muted" style={{ marginTop: 4 }}>
            Records this month: <strong>{s.records_this_month}</strong> · Days missed: <strong>{s.days_missed}</strong>
          </div>
        </div>
      ))}
      {stats.length === 0 && <div className="vault-muted">No habits yet</div>}
    </div>
  </div>
);
