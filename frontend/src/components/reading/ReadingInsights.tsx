import type { BookInsights } from '../../services/api';

interface ReadingInsightsProps {
  insights: BookInsights;
}

export const ReadingInsights = ({ insights }: ReadingInsightsProps) => (
  <div className="card" style={{ marginBottom: '1.5rem' }}>
    <h2 className="widget-title" style={{ marginBottom: '1rem' }}>📊 Reading Insights</h2>
    <div className="card-grid" style={{ marginBottom: '1rem' }}>
      <div className="stat-tile" style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius)', textAlign: 'center' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Total</div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{insights.total}</div>
      </div>
      <div className="stat-tile" style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius)', textAlign: 'center' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Reading</div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--info)' }}>{insights.reading}</div>
      </div>
      <div className="stat-tile" style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius)', textAlign: 'center' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Finished</div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--success)' }}>{insights.finished}</div>
      </div>
      <div className="stat-tile" style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius)', textAlign: 'center' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Want</div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--warning)' }}>{insights.want}</div>
      </div>
      <div className="stat-tile" style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius)', textAlign: 'center' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Completion</div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{insights.completion_pct}%</div>
      </div>
    </div>
    {Object.keys(insights.per_author).length > 0 && (
      <div>
        <h3 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Per Author</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {Object.entries(insights.per_author).map(([author, count]) => (
            <div key={author} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0.75rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', fontSize: '0.85rem' }}>
              <span>{author}</span>
              <span style={{ fontWeight: 600 }}>{count}</span>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);