import { useEffect, useRef, useState } from 'react';
import { useHabitTrackerData } from '../hooks/useHabitTrackerData';
import {
  HtHeader,
  HtStatusWindow,
  HtPomodoro,
  HtRewards,
  HtQuickActions,
  HtHabitModal,
  HtLifeAreasGrid,
  HtDailyGoodHabits,
  HtDailyBadHabits,
  HtCompletedCalendar,
} from '../components/habittracker';
import { ProgressBarsQC } from '../components/questcentre/ProgressBarsQC';
import { SkeletonBox } from '../components/shared/Skeleton';

/**
 * Gamified Habit Tracker dashboard (spec): fixed-sidebar layout — cinematic
 * header, Status-Window / Pomodoro / Rewards sidebar, Quick-Action +
 * Progress + Life-Areas row, Daily Good-Habit row, Daily Bad-Habit row, and
 * the two Completed-Good/Bad weekly calendar rows.
 */
export const GamifiedHabitTracker = () => {
  const { data, loading, errors, refresh } = useHabitTrackerData();
  const [modalKind, setModalKind] = useState<'good' | 'bad' | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const appliedTheme = useRef(false);

  useEffect(() => {
    if (appliedTheme.current) return;
    appliedTheme.current = true;
    const root = document.getElementById('habit-tracker-root');
    if (root) root.setAttribute('data-theme', 'habit-tracker');
  }, []);

  const handleChanged = () => {
    setRefreshKey((k) => k + 1);
    void refresh();
  };

  const totalXp = data.statusWindow?.character?.xp ?? data.summary?.total_xp ?? 0;

  return (
    <div id="habit-tracker-root">
      <HtHeader />

      {errors.length > 0 && (
        <div className="ht-card" style={{ margin: '1rem 0', borderColor: 'var(--ht-bad)' }}>
          <span style={{ color: 'var(--ht-bad)', fontSize: '0.78rem' }}>
            Some widgets failed to load: {errors.join(', ')}
          </span>
        </div>
      )}

      <div className="ht-layout">
        <aside className="ht-sidebar">
          {loading && !data.statusWindow ? (
            <>
              <div className="ht-skeleton-sidebar" />
              <div className="ht-skeleton-sidebar" style={{ height: 210 }} />
              <div className="ht-skeleton-sidebar" style={{ height: 200 }} />
            </>
          ) : (
            <>
              <HtStatusWindow statusWindow={data.statusWindow} />
              <HtPomodoro />
              <HtRewards
                rewards={data.summary?.rewards_available ?? []}
                totalXp={totalXp}
                onClaimed={handleChanged}
              />
            </>
          )}
        </aside>

        <div className="ht-main">
          {/* ── Row 1: Quick-Action + Progress | Life-Areas (Phases 62-68) ── */}
          <section className="ht-row">
            <div className="ht-row-1">
              <div className="ht-row" style={{ gap: '1.25rem' }}>
                <HtQuickActions onCreate={setModalKind} />
                {/* ProgressBarsQC renders its own card + title — keep it standalone. */}
                {loading && !data.progress ? (
                  <div className="ht-card"><SkeletonBox height={12} /></div>
                ) : (
                  <ProgressBarsQC progress={data.progress} />
                )}
              </div>
              <HtLifeAreasGrid areas={data.summary?.life_areas ?? []} />
            </div>
          </section>

          {/* ── Row 2: Daily Good Habits (Phases 69-76) ── */}
          <section className="ht-row">
            {loading && !data.goodHabits.length ? (
              <div className="ht-habit-scroll">
                {[0, 1, 2, 3].map((i) => <div key={i} className="ht-skeleton-card" />)}
              </div>
            ) : (
              <HtDailyGoodHabits
                habits={data.goodHabits}
                todayItems={data.todayItems}
                overviewDays={data.goodCalendar}
                onChanged={handleChanged}
              />
            )}
          </section>

          {/* ── Row 3: Daily Bad Habits (Phases 77-84) ── */}
          <section className="ht-row">
            {loading && !data.badHabits.length ? (
              <div className="ht-habit-scroll">
                {[0, 1, 2, 3].map((i) => <div key={i} className="ht-skeleton-card" />)}
              </div>
            ) : (
              <HtDailyBadHabits
                habits={data.badHabits}
                todayItems={data.todayItems}
                overviewDays={data.badCalendar}
                onChanged={handleChanged}
              />
            )}
          </section>

          {/* ── Row 4: Completed Good Habits calendar (Phases 85-91) ── */}
          <section className="ht-row">
            <HtCompletedCalendar type="good" refreshKey={refreshKey} />
          </section>

          {/* ── Row 5: Completed Bad Habits calendar ── */}
          <section className="ht-row">
            <HtCompletedCalendar type="bad" refreshKey={refreshKey} />
          </section>
        </div>
      </div>

      {modalKind && (
        <HtHabitModal kind={modalKind} onClose={() => setModalKind(null)} onCreated={handleChanged} />
      )}
    </div>
  );
};
