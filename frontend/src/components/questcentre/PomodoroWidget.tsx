import { useEffect, useRef, useState } from 'react';
import { usePomodoro } from '../../hooks/usePomodoro';
import { ProgressRing } from '../pomodoro/ProgressRing';
import { SettingsModal } from '../pomodoro/SettingsModal';

interface PomodoroWidgetProps {
  /** Fired once when a running timer reaches 00:00 (used to persist sessions). */
  onComplete?: (mode: 'focus' | 'break' | 'long-break', durationMinutes: number) => void;
}

/** Compact quest-centre Pomodoro widget (spec Row 1). */
export const PomodoroWidget = ({ onComplete }: PomodoroWidgetProps = {}) => {
  const { timer, running, mode, settings, progress, startFocus, startBreak, startLongBreak, tick, stop, updateSettings } = usePomodoro();
  const [showSettings, setShowSettings] = useState(false);
  const wasRunning = useRef(false);

  // Edge-detect completion: running → stopped at 00:00.
  useEffect(() => {
    if (wasRunning.current && !running && timer === 0) {
      const duration = mode === 'focus' ? settings.focusMinutes : mode === 'long-break' ? settings.longBreakMinutes : settings.breakMinutes;
      onComplete?.(mode, duration);
    }
    wasRunning.current = running;
  }, [running, timer, mode, settings, onComplete]);

  useEffect(() => {
    if (!running) return;
    const iv = window.setInterval(tick, 1000);
    return () => window.clearInterval(iv);
  }, [running, tick]);

  const mm = String(Math.floor(timer / 60)).padStart(2, '0');
  const ss = String(timer % 60).padStart(2, '0');

  const modeLabel =
    mode === 'focus' ? 'Focus' : mode === 'long-break' ? 'Long Break' : 'Short Break';

  return (
    <div className="qc-card">
      <div className="qc-card-title">Pomodoro</div>
      <div className="qc-pomodoro">
        <div className="pomodoro-ring-container">
          <ProgressRing progress={progress} size={160} strokeWidth={8} color="var(--qc-gold)" />
          <div className="pomodoro-time">{mm}:{ss}</div>
          <div className="pomodoro-mode-label">{modeLabel}</div>
        </div>

        <div className="qc-pomodoro-controls">
          <button type="button" className={`qc-btn ${running && mode !== 'focus' ? 'qc-btn-success' : 'qc-btn-gold'}`} onClick={startFocus}>
            {mode === 'focus' ? (running ? '▶️ Focus' : 'Start') : 'Focus'}
          </button>
          <button type="button" className="qc-btn" onClick={startBreak}>Short Break</button>
          <button type="button" className="qc-btn" onClick={startLongBreak}>Long Break</button>
          <button type="button" className="qc-btn" onClick={stop}>Stop</button>
          <button
            type="button"
            className="qc-btn-icon"
            onClick={() => setShowSettings(true)}
            aria-label="Timer settings"
            title="Settings"
          >
            ⚙️
          </button>
        </div>
      </div>

      {showSettings && (
        <SettingsModal
          focusMinutes={settings.focusMinutes}
          breakMinutes={settings.breakMinutes}
          onSave={(s) => updateSettings(s)}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
};
