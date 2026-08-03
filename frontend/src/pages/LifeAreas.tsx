import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { LifeArea } from '../services/api';

export const LifeAreas = () => {
  const [areas, setAreas] = useState<LifeArea[]>([]);

  useEffect(() => { endpoints.lifeAreas.list().then(setAreas).catch(() => {}); }, []);

  const avgScore = areas.length ? Math.round(areas.reduce((s, a) => s + a.satisfaction_score, 0) / areas.length * 10) / 10 : 0;

  const renderDots = (score: number) =>
    Array.from({ length: 10 }, (_, i) => (
      <span key={i} style={{ color: i < score ? 'var(--accent)' : 'var(--border)', fontSize: '1.25rem', lineHeight: 1 }}>●</span>
    ));

  return (
    <div>
      <Header title="Life Areas" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Areas Tracked</div><div className="value">{areas.length}</div></div>
        <div className="stat-tile"><div className="label">Avg Satisfaction</div><div className="value">{avgScore}/10</div></div>
      </div>
      <div className="card-grid">
        {areas.map((a) => (
          <div className="card" key={a.id}>
            <h3 style={{ marginBottom: '0.5rem' }}>{a.name}</h3>
            <div style={{ marginBottom: '0.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Satisfaction: {a.satisfaction_score}/10</div>
              <div>{renderDots(a.satisfaction_score)}</div>
            </div>
            {a.goal && (
              <div style={{ paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.15rem' }}>Goal</div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{a.goal}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
