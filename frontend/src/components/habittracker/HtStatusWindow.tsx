import type { HabitTrackerStatusWindow } from '../../services/api';

interface Props {
  statusWindow: HabitTrackerStatusWindow | null;
}

/** Time-based greeting (Phase 55). */
const greeting = (): string => {
  const h = new Date().getHours();
  if (h < 12) return 'Good Morning Player';
  if (h < 17) return 'Good Afternoon Player';
  return 'Good Evening Player';
};

const avatarEmoji = (klass: string | null): string => {
  if (klass === 'Wizard') return '🧙';
  if (klass === 'Warrior') return '⚔️';
  if (klass === 'Rogue') return '🗡️';
  return '🧝';
};

/** Sidebar Status-Window: wizard card + habit "Today's Stats" (Phases 54-55). */
export const HtStatusWindow = ({ statusWindow }: Props) => {
  if (!statusWindow || !statusWindow.character) {
    return (
      <div className="ht-card ht-status-window">
        <div className="ht-card-title">Status Window</div>
        <div className="ht-cal-empty">No character yet — seed the RPG module.</div>
      </div>
    );
  }

  const { character, xp_to_next, today_habits } = statusWindow;
  const goodToday = today_habits.filter((t) => t.habit_type !== 'bad').length;
  const badToday = today_habits.length - goodToday;
  const xpToday = today_habits.reduce((sum, t) => sum + t.xp_change, 0);

  return (
    <div className="ht-card ht-status-window">
      <div className="ht-card-title">Status Window</div>

      <div className="ht-sw-header">
        <div className="ht-sw-avatar" aria-hidden="true">{avatarEmoji(character.avatar_class)}</div>
        <div>
          <div className="ht-sw-name">{greeting()}</div>
          <div className="ht-sw-class">{character.class_name}</div>
        </div>
        <span className="ht-sw-level-badge" aria-label={`Level ${character.level}`}>Lv {character.level}</span>
      </div>

      <div>
        <div className="ht-xp-row">
          <span>Total XP</span>
          <span>{character.xp.toLocaleString()}</span>
        </div>
        <div className="ht-xp-bar" role="progressbar" aria-label="XP to next level" aria-valuenow={character.xp % 1000} aria-valuemin={0} aria-valuemax={1000}>
          <div className="ht-xp-fill" style={{ width: `${(character.xp % 1000) / 10}%` }} />
        </div>
        <div className="ht-xp-row">
          <span>{xp_to_next ?? 0} XP left to next level</span>
          {character.current_streak > 0 && (
            <span className="ht-sw-streak" aria-label={`${character.current_streak} day streak`}>🔥 {character.current_streak}</span>
          )}
        </div>
      </div>

      <div>
        <div className="ht-card-title" style={{ marginBottom: '0.35rem' }}>Today's Stats</div>
        {today_habits.length === 0 ? (
          <div className="ht-cal-empty">Nothing logged yet today — go earn some gold!</div>
        ) : (
          <div className="ht-today-list">
            {today_habits.map((t) => (
              <div key={t.id} className={`ht-today-item ${t.habit_type === 'bad' ? 'bad' : 'good'}`}>
                <span className="ht-today-text">{t.habit_name}</span>
                <span className={`ht-today-xp ${t.xp_change >= 0 ? 'plus' : 'minus'}`}>
                  {t.xp_change >= 0 ? '+' : ''}{t.xp_change} XP
                </span>
              </div>
            ))}
            <div className="ht-xp-row" style={{ marginTop: '0.25rem' }}>
              <span>Today net</span>
              <span style={{ fontWeight: 800, color: xpToday >= 0 ? 'var(--ht-good)' : 'var(--ht-bad)' }}>
                {xpToday >= 0 ? '+' : ''}{xpToday} XP
              </span>
            </div>
            <div className="ht-xp-row">
              <span>Good / Bad</span>
              <span>{goodToday} / {badToday}</span>
            </div>
          </div>
        )}
      </div>

      <div className="ht-keep-going">Keep going! 💪</div>
    </div>
  );
};
