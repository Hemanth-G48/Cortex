import { useState } from 'react';
import type { Habit } from '../../services/api';

interface Props {
  habit: Habit;
  loggedToday: boolean;
  busy: boolean;
  onAdmit: (habit: Habit) => Promise<void>;
  // Defect #48: tally derived from the habit's own log rows
  // (GET /habits/{id}/logs) rather than the counter cached on the habit row.
  daysCaught?: number;
}

/**
 * Row-3 bad-habit card (Phase 78-79, 82): moody thumbnail, "Shit I did it:
 * -X XP", red flash + "-X XP" fly-up on admit, days_caught counter.
 */
export const HtBadHabitCard = ({ habit, loggedToday, busy, onAdmit, daysCaught }: Props) => {
  const caught = daysCaught ?? habit.days_caught;
  const [flash, setFlash] = useState(false);
  const [flyUp, setFlyUp] = useState<string | null>(null);

  const handle = async () => {
    setFlash(true);
    setFlyUp(`-${habit.xp_penalty} XP`);
    setTimeout(() => {
      setFlash(false);
      setFlyUp(null);
    }, 900);
    await onAdmit(habit);
  };

  return (
    <div className={`ht-habit-card ht-bad-card${flash ? ' ht-card-flash-red' : ''}`}>
      {flyUp && <span className="ht-fly-up" aria-hidden="true">{flyUp}</span>}
      <div className="ht-habit-thumb" aria-hidden="true">
        {habit.image_url ? <img src={habit.image_url} alt="" /> : '🌑'}
      </div>
      <div>
        <div className="ht-habit-name">{habit.name}</div>
        <div className="ht-habit-penalty">Shit I did it: -{habit.xp_penalty} XP</div>
      </div>
      <div className="ht-habit-meta">
        <span>📉 caught {caught}x</span>
      </div>
      <div className={`ht-habit-today${loggedToday ? ' done' : ''}`}>
        {loggedToday ? '✓ Admitted Today' : 'Today'}
      </div>
      <button
        type="button"
        className="ht-admit-btn"
        onClick={() => void handle()}
        disabled={loggedToday || busy}
        aria-label={`Admit ${habit.name}`}
      >
        {loggedToday ? '✓ Admitted' : 'Shit I did it'}
      </button>
    </div>
  );
};
