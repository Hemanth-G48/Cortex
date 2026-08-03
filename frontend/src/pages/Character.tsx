import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { RpgLayout } from '../components/rpg/RpgLayout';
import { RpgCard } from '../components/rpg/RpgCard';
import { RpgBadge } from '../components/rpg/RpgBadge';
import { RpgButton } from '../components/rpg/RpgButton';
import { endpoints } from '../services/api';
import type { Character as CharacterType } from '../services/api';

const sidebar = (
  <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
    <Link to="/character" className="sidebar-link active" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>👤</span> Profile
    </Link>
    <Link to="/quests" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>⚔️</span> Quests
    </Link>
    <Link to="/missions" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>🎯</span> Missions
    </Link>
    <Link to="/rewards" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>🎁</span> Rewards
    </Link>
    <Link to="/rpg-dashboard" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>📊</span> Dashboard
    </Link>
  </nav>
);

function xpForNextLevel(level: number): number {
  return level * 1000;
}

function xpProgressBar(xp: number, level: number): number {
  const currentLevelXp = (level - 1) * 1000;
  const nextLevelXp = level * 1000;
  const progress = xp - currentLevelXp;
  const range = nextLevelXp - currentLevelXp;
  return Math.min(100, Math.max(0, (progress / range) * 100));
}

export const Character = () => {
  const [char, setChar] = useState<CharacterType | null>(null);
  const [addingXp, setAddingXp] = useState(false);

  useEffect(() => {
    endpoints.characters.get(1).then(setChar).catch(() => {});
  }, []);

  const handleAddXp = async (amount: number) => {
    setAddingXp(true);
    try {
      const updated = await endpoints.characters.addXp(1, amount);
      setChar(updated);
    } catch {
      /* ignore */
    } finally {
      setAddingXp(false);
    }
  };

  if (!char) {
    return <RpgLayout sidebar={sidebar}><p>Loading character...</p></RpgLayout>;
  }

  const xpPct = xpProgressBar(char.xp, char.level);
  const statData = [
    { label: 'STR', value: char.strength, color: 'var(--rpg-stat-str)' },
    { label: 'AGI', value: char.agility, color: 'var(--rpg-stat-agi)' },
    { label: 'INT', value: char.intelligence, color: 'var(--rpg-stat-int)' },
    { label: 'END', value: char.endurance, color: 'var(--rpg-stat-end)' },
  ];

  return (
    <RpgLayout sidebar={sidebar}>
      <div style={{ maxWidth: '600px', margin: '0 auto' }}>
        {/* ── Profile Header ── */}
        <RpgCard style={{ textAlign: 'center', marginBottom: '16px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '8px' }}>🧙</div>
          <h2 className="pixel-text" style={{ color: '#ff9800', margin: '0 0 4px 0', fontSize: '1.2rem' }}>
            {char.name}
          </h2>
          <RpgBadge variant="orange">{char.class_name}</RpgBadge>
          <div style={{ marginTop: '12px', fontSize: '0.8rem', color: '#b0b0b0' }}>
            Level <strong style={{ color: '#ffd700' }}>{char.level}</strong>
            <span style={{ marginLeft: '12px' }}>
              {char.xp} / {xpForNextLevel(char.level)} XP
            </span>
          </div>
          <div className="rpg-progress-bar" style={{ marginTop: '12px' }}>
            <div
              className="rpg-progress-fill-orange"
              style={{ width: `${xpPct}%` }}
            />
          </div>
        </RpgCard>

        {/* ── Stats Card ── */}
        <RpgCard style={{ marginBottom: '16px' }}>
          <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: '0 0 12px 0' }}>
            STATS
          </h3>
          {statData.map((s) => (
            <div key={s.label} className="rpg-stat-bar">
              <span className="rpg-stat-label" style={{ color: s.color }}>{s.label}</span>
              <div className="rpg-stat-track">
                <div
                  className="rpg-stat-fill"
                  style={{ width: `${(s.value / 20) * 100}%`, background: s.color }}
                />
              </div>
              <span className="rpg-stat-value">{s.value}</span>
            </div>
          ))}
        </RpgCard>

        {/* ── Equipped Badge ── */}
        <RpgCard style={{ marginBottom: '16px' }}>
          <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: '0 0 12px 0' }}>
            EQUIPPED BADGE
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '2rem' }}>🏅</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Quest Initiate</div>
              <RpgBadge variant="gold" style={{ marginTop: '4px' }}>Active</RpgBadge>
            </div>
          </div>
        </RpgCard>

        {/* ── Add XP ── */}
        <RpgCard>
          <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: '0 0 12px 0' }}>
            ADD XP
          </h3>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <RpgButton variant="orange" onClick={() => handleAddXp(10)} disabled={addingXp}>
              +10 XP
            </RpgButton>
            <RpgButton variant="orange" onClick={() => handleAddXp(50)} disabled={addingXp}>
              +50 XP
            </RpgButton>
            <RpgButton variant="green" onClick={() => handleAddXp(100)} disabled={addingXp}>
              +100 XP
            </RpgButton>
          </div>
        </RpgCard>
      </div>
    </RpgLayout>
  );
};
