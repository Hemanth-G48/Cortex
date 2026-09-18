import { useEffect, useState, useRef, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { PomodoroSession } from '../services/api';
import { usePomodoro } from '../hooks/usePomodoro';
import { ProgressRing } from '../components/pomodoro/ProgressRing';
import { SettingsModal } from '../components/pomodoro/SettingsModal';
import { BrainDumpWidget } from '../components/BrainDumpWidget';
import { playDing } from '../utils/sounds';

export const Pomodoro = () => {
  const [sessions, setSessions] = useState<PomodoroSession[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const pom = usePomodoro();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { endpoints.pomodoro.list().then(setSessions).catch(() => {}); }, []);

  // Defect #58: hydrate the timer from the user's stored preferences so the
  // durations follow the user (and survive reloads) instead of living only in
  // reducer state. Best-effort — an offline profile keeps the defaults.
  useEffect(() => {
    endpoints.kb.preferences
      .get()
      .then((p) => {
        pom.updateSettings({
          focusMinutes: p.session_length_mins,
          breakMinutes: p.pomodoro_break_mins,
        });
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hydrate once on mount
  }, []);

  const startFocus = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    pom.startFocus();
    playDing('focus');
    intervalRef.current = setInterval(() => {
      pom.tick();
    }, 1000);
  }, [pom]);

  const startBreak = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    pom.startBreak();
    playDing(pom.mode === 'focus' ? 'break' : 'long-break');
    intervalRef.current = setInterval(() => {
      pom.tick();
    }, 1000);
  }, [pom]);

  const stopTimer = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    pom.stop();
  }, [pom]);

  // Log completed session + defect #56 fix: also open a KB micro-session so the
  // pomodoro is tied to the vault session pipeline (mastery/xp), not just the
  // local pomodoro table.
  useEffect(() => {
    if (!pom.running && pom.timer === 0 && pom.mode === 'focus') {
      playDing('break');
      Promise.all([
        endpoints.pomodoro.create({
          start_time: new Date().toISOString(),
          duration_minutes: pom.settings.focusMinutes,
          completed: true,
          user_id: 1,
        }),
        // Best-effort KB session log — if the vault session pipeline is offline
        // the pomodoro still completes locally.
        endpoints.kb.sessions.start(1, pom.settings.focusMinutes)
          .then((s) => endpoints.kb.sessions.complete(s.session.id).catch(() => {}))
          .catch(() => {}),
      ]).then(() => endpoints.pomodoro.list().then(setSessions)).catch(() => {});
    }
  }, [pom.running, pom.timer, pom.mode, pom.settings.focusMinutes]);

  // Cleanup interval on unmount
  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current); }, []);

  const formatTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const timerColor = pom.mode === 'focus' ? 'var(--accent)' : 'var(--success)';

  // Defect #58: persist the chosen durations server-side (kb/preferences.py) so
  // they are the user's settings, not in-memory state.
  const handleSaveSettings = (s: { focusMinutes: number; breakMinutes: number }) => {
    pom.updateSettings(s);
    stopTimer();
    endpoints.kb.preferences
      .update({ session_length_mins: s.focusMinutes, pomodoro_break_mins: s.breakMinutes })
      .catch(() => {});
  };

  return (
    <div>
      <Header title="Pomodoro Timer" />
      <div className="pomodoro-center">
        <div className="pomodoro-ring-container">
          <ProgressRing progress={pom.progress} size={220} strokeWidth={8} color={timerColor} />
          <div className="pomodoro-time" style={{ color: timerColor }}>
            {formatTime(pom.timer)}
          </div>
          <div className="pomodoro-mode-label">{pom.mode === 'focus' ? 'FOCUS' : pom.mode === 'long-break' ? 'LONG BREAK' : 'BREAK'}</div>
        </div>

        <div className="pomodoro-controls">
          {!pom.running ? (
            <>
              <button className="badge badge-danger" style={{ cursor: 'pointer', border: 'none', padding: '0.5rem 1.25rem', fontSize: '0.9rem' }} onClick={startFocus}>Focus {pom.settings.focusMinutes}m</button>
              <button className="badge badge-success" style={{ cursor: 'pointer', border: 'none', padding: '0.5rem 1.25rem', fontSize: '0.9rem' }} onClick={startBreak}>Break {pom.settings.breakMinutes}m</button>
            </>
          ) : (
            <button className="badge badge-warning" style={{ cursor: 'pointer', border: 'none', padding: '0.5rem 1.25rem', fontSize: '0.9rem' }} onClick={stopTimer}>Stop</button>
          )}
          <button className="badge badge-info" style={{ cursor: 'pointer', border: 'none', padding: '0.5rem 1.25rem', fontSize: '0.9rem' }} onClick={() => setShowSettings(true)}>Settings</button>
        </div>
      </div>

      <div className="page-section" style={{ marginTop: '2rem' }}>
        <h2>Brain Dump</h2>
        <BrainDumpWidget />
      </div>

      <div className="page-section">
        <h2>Session History</h2>
        <div className="card">
          <table className="data-table">
            <thead><tr><th>Task</th><th>Duration</th><th>Status</th></tr></thead>
            <tbody>
              {sessions.slice(0, 10).map((s) => (
                <tr key={s.id}>
                  <td>{s.task_description ?? '—'}</td>
                  <td>{s.duration_minutes}min</td>
                  <td><span className={`badge badge-${s.completed ? 'success' : 'warning'}`}>{s.completed ? 'Done' : 'Interrupted'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showSettings && (
        <SettingsModal
          focusMinutes={pom.settings.focusMinutes}
          breakMinutes={pom.settings.breakMinutes}
          onSave={handleSaveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
};
