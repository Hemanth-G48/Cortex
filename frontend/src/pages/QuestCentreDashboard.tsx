import { useEffect, useRef } from 'react';
import { useToast } from '../hooks/useToast';
import { useQuestCentreData } from '../hooks/useQuestCentreData';
import { StatusWindowWidget } from '../components/questcentre/StatusWindowWidget';
import { ProgressBarsQC } from '../components/questcentre/ProgressBarsQC';
import { QuickActionsQC } from '../components/questcentre/QuickActionsQC';
import { PriorityWindow } from '../components/questcentre/PriorityWindow';
import { PomodoroWidget } from '../components/questcentre/PomodoroWidget';
import { LifeAreasGridQC } from '../components/questcentre/LifeAreasGridQC';
import { QuestCenter } from '../components/rpg/QuestCenter';
import { MissionCenter } from '../components/rpg/MissionCenter';
import { RewardCenter } from '../components/rpg/RewardCenter';
import { WeeklyCalendar } from '../components/rpg/WeeklyCalendar';

/**
 * Gamified Quest Centre dashboard (spec): sidebar Status-Window + progress +
 * quick actions + priority window, then Row 1 (pomodoro + life areas),
 * Rows 2-4 (quest / mission / reward centers) and the quests calendar.
 */
export const QuestCentreDashboard = () => {
  const { data, loading, errors, refresh, setData } = useQuestCentreData();
  const appliedTheme = useRef(false);
  const prevLevel = useRef<number | null>(null);
  const { toast } = useToast();

  // Apply the quest-centre gold theme to the wrapper on mount (Phase 33).
  useEffect(() => {
    if (appliedTheme.current) return;
    appliedTheme.current = true;
    const root = document.getElementById('quest-centre-root');
    if (root) root.setAttribute('data-theme', 'quest-centre');
  }, []);

  // Level-up toast (Phase 76): fire whenever a refresh shows a higher level.
  useEffect(() => {
    const level = data.statusWindow?.character?.level;
    if (level == null) return;
    if (prevLevel.current != null && level > prevLevel.current) {
      toast(`Level Up! Reached Lv.${level} 🏆`, 'success');
    }
    prevLevel.current = level;
  }, [data.statusWindow?.character?.level, toast]);

  // Keep life-areas data fresh after a mark-complete action.
  const handleLifeAreaChanged = async () => {
    try {
      const areas = await import('../services/api').then((m) => m.endpoints.questCentre.lifeAreas());
      setData((prev) => ({ ...prev, lifeAreas: areas }));
    } catch {
      /* silent */
    }
  };

  return (
    <div id="quest-centre-root">
      <div className="qc-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h1 className="qc-pixel-title" style={{ fontSize: '1rem' }}>🏆 Quest Centre</h1>
        <button type="button" className="qc-btn qc-btn-gold" onClick={() => void refresh()}>
          ⟳ Refresh
        </button>
      </div>

      {errors.length > 0 && (
        <div className="qc-card" style={{ marginBottom: '1rem', borderColor: 'var(--qc-locked)' }}>
          <span style={{ color: 'var(--qc-locked)', fontSize: '0.8rem' }}>
            Some widgets failed to load: {errors.join(', ')}
          </span>
        </div>
      )}

      <div className="qc-layout">
        <aside className="qc-sidebar">
          <StatusWindowWidget statusWindow={data.statusWindow} onXpRefresh={() => void refresh()} />
          <ProgressBarsQC progress={data.progress} />
          <QuickActionsQC />
          <PriorityWindow priority={data.priorityWindow} />
        </aside>

        <div className="qc-main">
          <section className="qc-row-1">
            <PomodoroWidget />
            <LifeAreasGridQC areas={data.lifeAreas} onChanged={handleLifeAreaChanged} />
          </section>

          {loading ? (
            <div className="qc-empty-pixel">⏳ Loading centres…</div>
          ) : (
            <>
              <section className="page-section">
                <h2>Quest Center</h2>
                <QuestCenter />
              </section>

              <section className="page-section">
                <h2>Mission Center</h2>
                <MissionCenter />
              </section>

              <section className="page-section">
                <h2>Reward Center</h2>
                <RewardCenter />
              </section>
            </>
          )}

          <section className="page-section">
            <h2>Quests Calendar</h2>
            <WeeklyCalendar />
          </section>
        </div>
      </div>
    </div>
  );
};
