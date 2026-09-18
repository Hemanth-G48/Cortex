import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints, profileApi } from '../services/api';
import type { AIHealth } from '../services/api';
import GoogleSyncCard from '../components/settings/GoogleSyncCard';
import AIProviderSettings from '../components/settings/AIProviderSettings';
import ModelPicker from '../components/settings/ModelPicker';
import { LearningPreferences } from '../components/kb/LearningPreferences';
import { useProfile } from '../hooks/useProfile';

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
  // Single-owner app: the owner profile (no login).
  const { profile: user } = useProfile();
  const [aiHealth, setAiHealth] = useState<AIHealth | null>(null);
  const [aiModels, setAiModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>(() => localStorage.getItem(AI_MODEL_KEY) ?? '');
  // Defect #65 fix: explicit save instead of instant silent writes.
  const [draftModel, setDraftModel] = useState<string>(selectedModel);
  const [modelNotice, setModelNotice] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [backingUp, setBackingUp] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [backupFile, setBackupFile] = useState<File | null>(null);
  const [replaceDb, setReplaceDb] = useState(false);
  const [backupNotice, setBackupNotice] = useState<string | null>(null);

  useEffect(() => {
    endpoints.ai.health().then(setAiHealth).catch(() => setAiHealth(null));
    endpoints.ai.models().then((r) => setAiModels(r.models)).catch(() => setAiModels([]));
    // Defect #96 fix: load the server-persisted model preference.
    profileApi.getPrefs()
      .then((r) => {
        const serverModel = typeof r.prefs?.ai_model === 'string' ? r.prefs.ai_model : '';
        if (serverModel) {
          localStorage.setItem(AI_MODEL_KEY, serverModel);
          setSelectedModel(serverModel);
          setDraftModel(serverModel);
        }
      })
      .catch(() => { /* offline: keep the localStorage value */ });
  }, []);

  // Defect #65 fix: model changes are staged until "Save" is clicked.
  const saveModel = async (model: string = draftModel) => {
    try {
      // Defect #96 fix: persist to the backend profile, not just localStorage.
      await profileApi.updatePrefs({ ai_model: model });
      if (model) localStorage.setItem(AI_MODEL_KEY, model);
      else localStorage.removeItem(AI_MODEL_KEY);
      setSelectedModel(model);
      setDraftModel(model);
      setModelNotice('✅ Model preference saved.');
    } catch (e) {
      setModelNotice(`⚠ Could not save preference: ${e instanceof Error ? e.message : 'backend unreachable'}`);
    }
  };

  const revertModel = () => {
    setDraftModel(selectedModel);
    setModelNotice('Reverted to the saved preference.');
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
      // Defect #66 fix: KB data (documents + sources) included in the export.
      ['kb-documents', () => endpoints.kb.documents.list({}).then((r) => r.items ?? r).catch(() => null)],
      ['kb-sources', () => endpoints.kb.sources.list().then((r) => r.items ?? r).catch(() => null)],
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

  const exportBackup = async () => {
    setBackingUp(true);
    setBackupNotice(null);
    try {
      await endpoints.kb.backup.export();
      setBackupNotice('✅ Backup downloaded.');
    } catch (e) {
      setBackupNotice(`⚠ ${e instanceof Error ? e.message : 'Backup failed'}`);
    } finally {
      setBackingUp(false);
    }
  };

  const restoreBackup = async () => {
    if (!backupFile) return;
    setRestoring(true);
    setBackupNotice(null);
    try {
      const res = await endpoints.kb.backup.restore(backupFile, replaceDb);
      const lines = [
        `✅ Restored ${res.restored_files} vault file(s) across ${res.sources_matched} source(s).`,
      ];
      if (res.database_restored) lines.push('🗄️ Database snapshot applied — restart the backend to reconnect.');
      if (res.database_skipped) lines.push('🗄️ Database snapshot was not applied (safe default).');
      res.warnings.forEach((w) => lines.push(`⚠ ${w}`));
      setBackupNotice(lines.join('\n'));
      setBackupFile(null);
    } catch (e) {
      setBackupNotice(`⚠ ${e instanceof Error ? e.message : 'Restore failed'}`);
    } finally {
      setRestoring(false);
    }
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
          <AIProviderSettings />
          <div className="settings-ai">
            <div className="stat-row">
              <span className={`badge ${aiHealth?.available ? 'badge-success' : 'badge-muted'}`}>
                {aiHealth?.available
                  ? `AI enabled · ${aiHealth.model ?? aiHealth.active_provider?.model ?? 'default model'}${aiHealth.active_provider ? ` via ${aiHealth.active_provider.name}` : ''}`
                  : 'AI offline — using deterministic fallbacks'}
              </span>
              {aiHealth?.available && aiHealth.mode ? <span className="muted">mode: {aiHealth.mode}</span> : null}
            </div>
            {aiModels.length > 0 && (
              <div className="field-row">
                <label htmlFor="ai-model">
                  Model override{' '}
                  <span className="muted">({aiModels.length} models — dropdown, type to search)</span>
                </label>
                <ModelPicker
                  models={aiModels}
                  value={draftModel}
                  defaultModel={aiHealth?.model ?? null}
                  placeholder={`Search ${aiModels.length} models… (e.g. auto/best-free)`}
                  onSelect={(m) => setDraftModel(m)}
                />
                {(draftModel !== selectedModel || draftModel) && (
                  <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <button type="button" className="btn btn-sm btn-primary" onClick={() => void saveModel()}>
                      💾 Save model
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost"
                      onClick={revertModel}
                      title="Discard the staged change"
                    >
                      ↩ Undo
                    </button>
                  </span>
                )}
                {selectedModel && draftModel === selectedModel && (
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    title="Reset to the backend default model"
                    onClick={() => { void saveModel(''); }}
                  >
                    ✕ Reset to default
                  </button>
                )}
                {modelNotice && <span className="muted">{modelNotice}</span>}
              </div>
            )}
            <p className="muted settings-hint">
              Every AI feature falls back to a deterministic local generator when the provider is unreachable, so
              the app always works offline. Manage providers above — configure Ollama, LM Studio, or any
              OpenAI-compatible endpoint and switch models without touching code.
            </p>
          </div>
        </Section>

        <GoogleSyncCard />

        <Section title="🎓 Learning Preferences">
          <LearningPreferences />
        </Section>

        <Section title="🎨 Appearance">
          <div className="settings-row">
            <div>
              <div>Theme</div>
              <div className="muted">Use the theme switcher in the sidebar to choose between available themes.</div>
            </div>
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

        <Section title="🗄️ Vault Backup">
          <div className="settings-row">
            <div>
              <div>Download full vault backup</div>
              <div className="muted">
                A timestamped zip of your Second Brain vault files plus a consistent snapshot of the database.
                Keep it somewhere safe and use Restore to recover.
              </div>
            </div>
            <button className="btn" onClick={() => void exportBackup()} disabled={backingUp}>
              <span className="emoji">📦</span> {backingUp ? 'Building…' : 'Backup vault'}
            </button>
          </div>
          <div className="settings-row">
            <div>
              <div>Restore from backup</div>
              <div className="muted">
                Pick a vault-backup zip. Vault files are always restored into their original folders; the database
                snapshot is only applied when the checkbox below is enabled (safe default — never overwrites live data).
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.5rem', fontSize: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={replaceDb}
                  onChange={(e) => setReplaceDb(e.target.checked)}
                />
                Also replace the database snapshot (restart backend afterwards)
              </label>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', alignItems: 'flex-end' }}>
              <input
                type="file"
                accept=".zip,application/zip"
                onChange={(e) => setBackupFile(e.target.files?.[0] ?? null)}
                style={{ fontSize: '0.75rem', maxWidth: 260 }}
              />
              <button
                className="btn"
                onClick={() => void restoreBackup()}
                disabled={restoring || !backupFile}
              >
                <span className="emoji">♻️</span> {restoring ? 'Restoring…' : 'Restore backup'}
              </button>
            </div>
          </div>
          {backupNotice && (
            <p
              className="muted"
              style={{
                fontSize: '0.78rem', marginTop: '0.5rem', padding: '0.5rem 0.75rem', borderRadius: 8,
                background: backupNotice.startsWith('⚠') ? 'var(--warning-muted)' : 'var(--success-muted)',
                color: backupNotice.startsWith('⚠') ? 'var(--warning)' : 'var(--success)',
                whiteSpace: 'pre-wrap',
              }}
            >
              {backupNotice}
            </p>
          )}
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
