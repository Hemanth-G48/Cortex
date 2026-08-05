import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { AIHealth, User } from '../services/api';
import GoogleSyncCard from '../components/settings/GoogleSyncCard';

const AI_MODEL_KEY = 'slos-ai-model';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ marginBottom: '1.25rem', padding: '1.25rem 1.5rem' }}>
      <h3 className="section-title">{title}</h3>
      {children}
    </div>
  );
}

export const Settings = () => {
  const [user, setUser] = useState<User | null>(null);
  const [aiHealth, setAiHealth] = useState<AIHealth | null>(null);
  const [aiModels, setAiModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>(() => localStorage.getItem(AI_MODEL_KEY) ?? '');
  const [exporting, setExporting] = useState(false);

  const loadUser = useCallback(() => {
    endpoints.login().then((r) => setUser(r.user)).catch(() => {});
  }, []);

  useEffect(() => {
    loadUser();
    endpoints.ai.health().then(setAiHealth).catch(() => setAiHealth(null));
    endpoints.ai.models().then((r) => setAiModels(r.models)).catch(() => setAiModels([]));
  }, [loadUser]);

  const saveModel = (model: string) => {
    setSelectedModel(model);
    if (model) localStorage.setItem(AI_MODEL_KEY, model);
    else localStorage.removeItem(AI_MODEL_KEY);
  };

  const exportData = async () => {
    setExporting(true);
    const keys: [string, () => Promise<unknown>][] = [
      ['courses', () => endpoints.courses.list()],
      ['assignments', () => endpoints.assignments.list()],
      ['exams', () => endpoints.exams.list()],
      ['notes', () => endpoints.notes.list()],
      ['tasks', () => endpoints.tasks.list()],
      ['habits', () => endpoints.habits.list(true)],
      ['goals', () => endpoints.goals.list()],
      ['grades', () => endpoints.grades.list()],
      ['gpa', () => endpoints.grades.gpa()],
      ['flashcard-decks', () => endpoints.flashcards.list()],
      ['study-plans', () => endpoints.studyPlans.list()],
      ['quests', () => endpoints.quests.list()],
      ['projects', () => endpoints.projects.list()],
      ['life-areas', () => endpoints.lifeAreas.list()],
      ['journal', () => endpoints.journal.list()],
      ['pomodoro-sessions', () => endpoints.pomodoro.list()],
      ['schedule', () => endpoints.schedule.list()],
      ['google-status', () => endpoints.google.status()],
    ];
    const out: Record<string, unknown> = { exported_at: new Date().toISOString() };
    const results = await Promise.allSettled(keys.map(([k, fn]) => fn().then((v) => [k, v] as const)));
    results.forEach((r) => {
      if (r.status === 'fulfilled') out[r.value[0]] = r.value[1];
    });
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `slos-data-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setExporting(false);
  };

  const initial = (user?.name ?? 'S')[0]?.toUpperCase() ?? 'S';

  return (
    <div>
      <Header title="Settings" />
      <div className="settings-page">
        <Section title="👤 Profile">
          <div className="settings-profile">
            <div className="settings-avatar">{initial}</div>
            <div>
              <div className="settings-name">{user?.name ?? 'Student'}</div>
              <div className="muted">Level {user?.current_level ?? '—'} · {user?.total_xp ?? 0} XP · {user?.current_streak ?? 0}-day streak</div>
            </div>
          </div>
        </Section>

        <Section title="🤖 AI">
          <div className="settings-ai">
            <div className="stat-row">
              <span className={`badge ${aiHealth?.available ? 'badge-success' : 'badge-muted'}`}>
                {aiHealth?.available ? `AI enabled · ${aiHealth.model ?? 'default model'}` : 'AI offline — using deterministic fallbacks'}
              </span>
              {aiHealth?.available && aiHealth.mode ? <span className="muted">mode: {aiHealth.mode}</span> : null}
            </div>
            {aiModels.length > 0 && (
              <div className="field-row">
                <label htmlFor="ai-model">Model override (stored locally)</label>
                <select id="ai-model" value={selectedModel} onChange={(e) => saveModel(e.target.value)}>
                  <option value="">Use backend default</option>
                  {aiModels.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <p className="muted settings-hint">
              Every AI feature falls back to a deterministic local generator when the provider is unreachable, so
              the app always works offline.
            </p>
          </div>
        </Section>

        <GoogleSyncCard />

        <Section title="🎨 Appearance">
          <div className="settings-row">
            <div>
              <div>Theme</div>
              <div className="muted">Dark theme (more themes coming soon)</div>
            </div>
            <span className="badge badge-info">Dark</span>
          </div>
        </Section>

        <Section title="📦 Data">
          <div className="settings-row">
            <div>
              <div>Export all data</div>
              <div className="muted">Download a JSON snapshot of your courses, assignments, habits, grades and more.</div>
            </div>
            <button className="btn" onClick={() => void exportData()} disabled={exporting}>
              <span className="emoji">⬇️</span> {exporting ? 'Exporting…' : 'Export JSON'}
            </button>
          </div>
        </Section>

        <Section title="ℹ️ About">
          <div className="settings-row">
            <div>Version</div>
            <span>Student Life OS · Shiori parity</span>
          </div>
          <div className="settings-row">
            <div>Keyboard shortcuts</div>
            <span className="muted">Press <kbd>?</kbd> anywhere to see them</span>
          </div>
        </Section>
      </div>
    </div>
  );
};
