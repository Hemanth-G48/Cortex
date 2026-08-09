import { useCallback, useEffect, useState } from 'react';
import { endpoints, type UserPreference } from '../../services/api';

const DEPTHS = [
  { value: 'overview', label: 'Overview first', hint: 'Big picture before details' },
  { value: 'deep_dive', label: 'Deep dive', hint: 'Full derivations and nuance' },
] as const;

const STYLES = [
  { value: 'concise', label: 'Concise', hint: 'Short, to the point' },
  { value: 'detailed', label: 'Detailed', hint: 'Thorough and complete' },
] as const;

const EXPLANATION_STYLES = [
  { value: 'plain', label: 'Plain English', hint: 'Simple words, minimal jargon' },
  { value: 'analogy', label: 'Analogies', hint: 'Connect to familiar ideas' },
  { value: 'formal', label: 'Formal', hint: 'Precise academic register' },
] as const;

const DEFAULT_PREFS: UserPreference = {
  depth: 'overview',
  examples_vs_theory: 0.5,
  style: 'concise',
  session_length_mins: 30,
  explanation_style: 'plain',
  onboarding_completed: false,
};

/**
 * Phase 8 (Idea 71) — learning-preference survey. One profile per user,
 * injected into the tutor + explanation prompts. Every field is validated on
 * the backend (clamped/whitelisted), so the UI only submits allowed values.
 */
export const LearningPreferences = () => {
  const [prefs, setPrefs] = useState<UserPreference>(DEFAULT_PREFS);
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    endpoints.kb.preferences
      .get()
      .then((p) => setPrefs({ ...DEFAULT_PREFS, ...p }))
      .catch(() => setPrefs(DEFAULT_PREFS))
      .finally(() => setLoaded(true));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    setBusy(true);
    try {
      const updated = await endpoints.kb.preferences.update(prefs);
      setPrefs(updated);
      setSaved(`Saved — ${new Date().toLocaleTimeString()}`);
    } catch (e) {
      setSaved(`Failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) {
    return <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Loading preferences…</p>;
  }

  return (
    <div>
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        How do you like to learn? These preferences shape the AI tutor and personalized
        explanations — they're never arbitrary; every field is validated.
      </p>

      {/* Depth */}
      <div className="field-row">
        <label>Preferred depth</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {DEPTHS.map((d) => (
            <label key={d.value} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', cursor: 'pointer', fontSize: '0.8rem' }}>
              <input
                type="radio"
                name="kb-depth"
                checked={prefs.depth === d.value}
                onChange={() => setPrefs((p) => ({ ...p, depth: d.value }))}
              />
              <span>
                <strong>{d.label}</strong>
                <span style={{ display: 'block', color: 'var(--text-muted)', fontSize: '0.7rem' }}>{d.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Verbosity style */}
      <div className="field-row">
        <label>Answer style</label>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          {STYLES.map((s) => (
            <button
              key={s.value}
              type="button"
              className={`btn btn-sm ${prefs.style === s.value ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setPrefs((p) => ({ ...p, style: s.value }))}
              title={s.hint}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Explanation register */}
      <div className="field-row">
        <label>Explanation style</label>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {EXPLANATION_STYLES.map((s) => (
            <button
              key={s.value}
              type="button"
              className={`btn btn-sm ${prefs.explanation_style === s.value ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setPrefs((p) => ({ ...p, explanation_style: s.value }))}
              title={s.hint}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Examples vs theory slider */}
      <div className="field-row">
        <label>
          Examples vs theory — <strong>{Math.round(prefs.examples_vs_theory * 100)}%</strong> examples
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={prefs.examples_vs_theory}
          onChange={(e) => setPrefs((p) => ({ ...p, examples_vs_theory: Number(e.target.value) }))}
          style={{ width: '100%', maxWidth: 360 }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', maxWidth: 360 }}>
          <span>Pure theory</span>
          <span>Examples-first</span>
        </div>
      </div>

      {/* Session length */}
      <div className="field-row">
        <label>Preferred session length</label>
        <select
          value={prefs.session_length_mins}
          onChange={(e) => setPrefs((p) => ({ ...p, session_length_mins: Number(e.target.value) }))}
        >
          {[15, 25, 30, 45, 60, 90, 120].map((m) => (
            <option key={m} value={m}>{m} minutes</option>
          ))}
        </select>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          Suggested study sessions and recommendations respect this.
        </span>
      </div>

      {/* Onboarding complete */}
      <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem', marginTop: '0.75rem', cursor: 'pointer' }}>
        <input
          type="checkbox"
          checked={prefs.onboarding_completed}
          onChange={(e) => setPrefs((p) => ({ ...p, onboarding_completed: e.target.checked }))}
        />
        I've completed the learning survey — use these preferences now
      </label>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1rem' }}>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => void save()} disabled={busy}>
          {busy ? 'Saving…' : 'Save preferences'}
        </button>
        {saved && <span style={{ fontSize: '0.72rem', color: saved.startsWith('Failed') ? 'var(--danger, #ef4444)' : 'var(--success, #10b981)' }}>{saved}</span>}
      </div>
    </div>
  );
};
