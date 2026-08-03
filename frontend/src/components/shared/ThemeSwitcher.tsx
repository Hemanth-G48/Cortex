import { useEffect, useState } from 'react';

export type ThemeId = 'student-os' | 'rpg' | 'vault' | 'life-planner' | 'quest-centre' | 'habit-tracker' | 'fitness-hub';

const THEMES: { id: ThemeId; label: string; icon: string }[] = [
  { id: 'student-os', label: 'Student OS', icon: '🎓' },
  { id: 'rpg', label: 'RPG', icon: '⚔️' },
  { id: 'vault', label: 'Vault', icon: '🗄️' },
  { id: 'life-planner', label: 'Life Planner', icon: '🌱' },
  { id: 'quest-centre', label: 'Quest Centre', icon: '🏆' },
  { id: 'habit-tracker', label: 'Habit Tracker', icon: '🔥' },
  { id: 'fitness-hub', label: 'Fitness Hub', icon: '💪' },
];

const STORAGE_KEY = 'student-os-theme';

/** Theme switcher — sets data-theme on <html> and persists the choice. */
export const ThemeSwitcher = () => {
  // Lazy initializer avoids a flash of the default theme on reload: the
  // data-theme attribute is written synchronously before the first paint.
  const [theme, setTheme] = useState<ThemeId>(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeId | null;
    const initial = saved && THEMES.some((t) => t.id === saved) ? saved : 'student-os';
    document.documentElement.setAttribute('data-theme', initial);
    return initial;
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const apply = (id: ThemeId) => {
    setTheme(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  return (
    <div className="theme-switcher" role="group" aria-label="Theme">
      {THEMES.map((t) => (
        <button
          key={t.id}
          type="button"
          className={`theme-switcher-btn${theme === t.id ? ' active' : ''}`}
          onClick={() => apply(t.id)}
          title={t.label}
          aria-label={`Switch to ${t.label} theme`}
          aria-pressed={theme === t.id}
        >
          {t.icon}
        </button>
      ))}
    </div>
  );
};
