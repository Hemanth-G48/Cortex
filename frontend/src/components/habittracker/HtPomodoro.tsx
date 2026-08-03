import { PomodoroWidget } from '../questcentre/PomodoroWidget';
import { endpoints } from '../../services/api';

/**
 * Sidebar Pomodoro (Phases 56-57): reuses the shared quest-centre widget and
 * persists a session with its mode (Focus / Break) whenever a timer completes.
 */
export const HtPomodoro = () => {
  const handleComplete = async (mode: 'focus' | 'break' | 'long-break', durationMinutes: number) => {
    try {
      await endpoints.pomodoro.create({
        user_id: 1,
        start_time: new Date().toISOString(),
        duration_minutes: durationMinutes,
        completed: true,
        mode: mode === 'focus' ? 'Focus' : 'Break',
        task_description: mode === 'focus' ? 'Focus session' : 'Break session',
      });
    } catch {
      /* session persistence is best-effort */
    }
  };

  return (
    <div className="ht-card ht-pomodoro-card">
      <div className="ht-card-title">Pomodoro Timer</div>
      <PomodoroWidget onComplete={(mode, duration) => void handleComplete(mode, duration)} />
    </div>
  );
};
