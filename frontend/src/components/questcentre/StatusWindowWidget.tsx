import { useToast } from '../../hooks/useToast';
import { endpoints } from '../../services/api';
import type { StatusWindow } from '../../services/api';

interface Props {
  statusWindow: StatusWindow | null;
  onXpRefresh?: () => void;
}

/**
 * Sidebar Status-Window (spec): wizard avatar card with greeting, level,
 * Total XP, "XP left to next level", and a today-task checklist.
 */
export const StatusWindowWidget = ({ statusWindow, onXpRefresh }: Props) => {
  const { toast } = useToast();

  if (!statusWindow || !statusWindow.character) {
    return (
      <div className="qc-card qc-status-window">
        <div className="qc-card-title">Status Window</div>
        <div className="qc-empty-note">No character yet — seed the RPG module.</div>
      </div>
    );
  }

  const { character, xp_to_next, today_tasks } = statusWindow;

  const toggleTask = async (id: number, done: boolean) => {
    if (done) return; // only forward-complete to avoid re-awarding
    try {
      const q = await endpoints.quests.complete(id);
      toast(`Quest Complete! +${q.xp_reward} XP`, 'success');
      onXpRefresh?.();
    } catch {
      toast('Could not complete quest', 'error');
    }
  };

  const avatarEmoji =
    character.avatar_class === 'Wizard' ? '🧙' : character.avatar_class === 'Warrior' ? '⚔️' : '🧝';

  return (
    <div className="qc-card qc-status-window">
      <div className="qc-card-title qc-pixel-title">Status Window</div>

      <div className="qc-sw-header">
        <div className="qc-sw-avatar" aria-hidden="true">{avatarEmoji}</div>
        <div>
          <div className="qc-sw-name">{character.name}</div>
          <div className="qc-sw-class">{character.class_name}</div>
        </div>
        <div className="qc-sw-level-badge" aria-label={`Level ${character.level}`}>
          Lv {character.level}
        </div>
      </div>

      <div>
        <div className="qc-xp-row">
          <span>Total XP</span>
          <span>{character.xp.toLocaleString()}</span>
        </div>
        <div className="qc-xp-bar" role="progressbar" aria-label="XP to next level" aria-valuenow={character.xp % 1000} aria-valuemin={0} aria-valuemax={1000}>
          <div className="qc-xp-fill" style={{ width: `${(character.xp % 1000) / 10}%` }} />
        </div>
        <div className="qc-xp-row">
          <span>{xp_to_next ?? 0} XP left to next level</span>
          {character.current_streak > 0 && (
            <span className="qc-sw-streak" aria-label={`${character.current_streak} day streak`}>
              🔥 {character.current_streak}
            </span>
          )}
        </div>
      </div>

      <div>
        <div className="qc-card-title" style={{ marginBottom: '0.35rem' }}>Today's Tasks</div>
        {today_tasks.length === 0 ? (
          <div className="qc-empty-note">All caught up — no quests due today.</div>
        ) : (
          <div className="qc-today-list">
            {today_tasks.map((t) => {
              const done = t.status === 'Completed';
              return (
                <label key={t.id} className={`qc-today-item${done ? ' done' : ''}`}>
                  <input
                    type="checkbox"
                    className="qc-today-check"
                    checked={done}
                    onChange={() => void toggleTask(t.id, done)}
                    aria-label={`Mark ${t.title} done`}
                  />
                  <span className="qc-today-text">{t.title}</span>
                  <span className="qc-today-xp">+{t.xp_reward} XP</span>
                </label>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
