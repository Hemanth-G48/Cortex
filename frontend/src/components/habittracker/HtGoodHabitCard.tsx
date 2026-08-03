import { useState } from 'react';
import type { Habit } from '../../services/api';

interface Props {
  habit: Habit;
  loggedToday: boolean;
  busy: boolean;
  onComplete: (habit: Habit) => Promise<void>;
}

/**
 * Row-2 good-habit card (Phase 70, 72, 74): 3D thumbnail, "Complete to earn:
 * X XP", Today placeholder vs ✓ Completed, green pop flash on complete.
 */
export const HtGoodHabitCard = ({ habit, loggedToday, busy, onComplete }: Props) => {
  const [flash, setFlash] = useState(false);

  const handle = async () => {
    setFlash(true);
    setTimeout(() => setFlash(false), 600);
    await onComplete(habit);
  };

  return (
    <div className={`ht-habit-card ht-good-card${flash ? ' ht-card-flash' : ''}`}>
      <div className="ht-habit-thumb" aria-hidden="true">
        {habit.image_url ? <img src={habit.image_url} alt="" /> : '🌱'}
      </div>
      <div>
        <div className="ht-habit-name">{habit.name}</div>
        <div className="ht-habit-reward">Complete to earn: {habit.xp_reward} XP</div>
      </div>
      <div className="ht-habit-meta">
        <span>🔥 {habit.current_streak}d streak</span>
        <span>Best {habit.longest_streak}d</span>
      </div>
      <div className={`ht-habit-today${loggedToday ? ' done' : ''}`}>
        {loggedToday ? '✓ Completed Today' : 'Today'}
      </div>
      <button
        type="button"
        className="ht-complete-btn"
        onClick={() => void handle()}
        disabled={loggedToday || busy}
        aria-label={`Complete ${habit.name}`}
      >
        {loggedToday ? '✓ Done' : 'Complete'}
      </button>
    </div>
  );
};
