import { useEffect, useState, useRef, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { PomodoroSession } from '../services/api';
import { usePomodoro } from '../hooks/usePomodoro';
import { ProgressRing } from '../components/pomodoro/ProgressRing';
import { SettingsModal } from '../components/pomodoro/SettingsModal';

export const Pomodoro = () => {
  const [sessions, setSessions] = useState<PomodoroSession[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const pom = usePomodoro();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { endpoints.pomodoro.list().then(setSessions).catch(() => {}); }, []);

  const startFocus = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    pom.startFocus();
    intervalRef.current = setInterval(() => {
      pom.tick();
    }, 1000);
  }, [pom]);

  const startBreak = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    pom.startBreak();
    intervalRef.current = setInterval(() => {
      pom.tick();
    }, 1000);
  }, [pom]);

  const stopTimer = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    pom.stop();
  }, [pom]);

  // Log completed session
  useEffect(() => {
    if (!pom.running && pom.timer === 0 && pom.mode === 'focus') {
      endpoints.pomodoro.create({
        start_time: new Date().toISOString(),
        duration_minutes: pom.settings.focusMinutes,
        completed: true,
        user_id: 1,
      }).then(() => {
        endpoints.pomodoro.list().then(setSessions);
      });
    }
  }, [pom.running, pom.timer, pom.mode, pom.settings.focusMinutes]);

  // Cleanup interval on unmount
  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current); }, []);

  const formatTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const timerColor = pom.mode === 'focus' ? 'var(--accent)' : 'var(--success)';

  const handleSaveSettings = (s: { focusMinutes: number; breakMinutes: number }) => {
    pom.updateSettings(s);
    stopTimer();
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
