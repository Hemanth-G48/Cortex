import { useCallback, useEffect, useState } from 'react';
import { confirmDelete } from '../../utils/confirm';
import { endpoints } from '../../services/api';
import type {
  AIProviderConfig,
  AIProviderTestResult,
  AIProviderType,
} from '../../services/api';

/**
 * AI Provider Settings (local-first, single-user).
 *
 * Lets the user manage a registry of AI providers — Ollama / LM Studio /
 * custom OpenAI-compatible endpoints on their own machine, plus OpenAI,
 * Anthropic, Google and any custom URL — without touching source code.
 * API keys are stored server-side in a git-ignored JSON file and are
 * write-only (the API never returns the raw key, only a preview).
 */

const PROVIDER_TYPES: { value: AIProviderType; label: string; local: boolean }[] = [
  { value: 'custom', label: 'Custom (OpenAI-compatible)', local: false },
  { value: 'ollama', label: 'Ollama (local)', local: true },
  { value: 'lmstudio', label: 'LM Studio (local)', local: true },
  { value: 'openai', label: 'OpenAI', local: false },
  { value: 'anthropic', label: 'Anthropic', local: false },
  { value: 'google', label: 'Google Gemini', local: false },
];

// Mirrors backend DEFAULT_BASE_URLS (prefill convenience only — always editable).
const DEFAULT_BASE_URLS: Record<AIProviderType, string> = {
  custom: 'http://localhost:11434/v1',
  openai: 'https://api.openai.com/v1',
  ollama: 'http://localhost:11434/v1',
  lmstudio: 'http://localhost:1234/v1',
  anthropic: 'https://api.anthropic.com',
  google: 'https://generativelanguage.googleapis.com',
};

function typeLabel(t: AIProviderType): string {
  return PROVIDER_TYPES.find((p) => p.value === t)?.label ?? t;
}

interface DraftForm {
  name: string;
  provider_type: AIProviderType;
  base_url: string;
  api_key: string;
  model: string;
  enabled: boolean;
  is_default: boolean;
}

const EMPTY_DRAFT: DraftForm = {
  name: '',
  provider_type: 'custom',
  base_url: DEFAULT_BASE_URLS.custom,
  api_key: '',
  model: '',
  enabled: true,
  is_default: false,
};

export default function AIProviderSettings() {
  const [providers, setProviders] = useState<AIProviderConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Add / edit form state. `editingId === null` → adding a new provider.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftForm>(EMPTY_DRAFT);
  const [saving, setSaving] = useState(false);

  // Per-provider async action state.
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; result: AIProviderTestResult } | null>(null);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    endpoints.ai.providers
      .list()
      .then((r) => {
        setProviders(r.providers);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const flash = (msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 3500);
  };

  const startAdd = () => {
    setEditingId(null);
    setDraft(EMPTY_DRAFT);
    setTestResult(null);
  };

  const startEdit = (p: AIProviderConfig) => {
    setEditingId(p.id);
    setDraft({
      name: p.name,
      provider_type: p.provider_type,
      base_url: p.base_url,
      api_key: '',
      model: p.model ?? '',
      enabled: p.enabled,
      is_default: p.is_default,
    });
    setTestResult(null);
  };

  const changeType = (t: AIProviderType) => {
    // Prefill the default base URL for the chosen type when the user is
    // adding a provider (never clobber an edit they already made).
    setDraft((d) => ({
      ...d,
      provider_type: t,
      base_url: editingId === null ? DEFAULT_BASE_URLS[t] : d.base_url,
    }));
  };

  const save = async () => {
    if (!draft.name.trim()) {
      setError('Give this provider a name.');
      return;
    }
    if (!draft.base_url.trim()) {
      setError('Enter a base URL (e.g. http://localhost:11434/v1).');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editingId === null) {
        const created = await endpoints.ai.providers.create({
          name: draft.name.trim(),
          provider_type: draft.provider_type,
          base_url: draft.base_url.trim(),
          api_key: draft.api_key || null,
          model: draft.model.trim() || null,
          enabled: draft.enabled,
          is_default: draft.is_default,
        });
        flash(`Provider "${created.name}" added.`);
      } else {
        const updated = await endpoints.ai.providers.update(editingId, {
          name: draft.name.trim(),
          provider_type: draft.provider_type,
          base_url: draft.base_url.trim(),
          api_key: draft.api_key || null,
          model: draft.model.trim() || null,
          enabled: draft.enabled,
          is_default: draft.is_default,
        });
        flash(`Provider "${updated.name}" updated.`);
      }
      setEditingId(null);
      setDraft(EMPTY_DRAFT);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async (id: string) => {
    setTestingId(id);
    setTestResult(null);
    try {
      const result = await endpoints.ai.providers.test(id);
      setTestResult({ id, result });
      if (result.ok && result.models?.length) {
        // Keep the model picker fresh after a successful test.
        load();
      }
    } catch (e) {
      setTestResult({ id, result: { ok: false, message: (e as Error).message } });
    } finally {
      setTestingId(null);
    }
  };

  const refreshModels = async (id: string) => {
    setRefreshingId(id);
    setError(null);
    try {
      const updated = await endpoints.ai.providers.refreshModels(id);
      if (updated.models?.length) {
        flash(`Model list refreshed — ${updated.models.length} models available.`);
      } else {
        setError('Could not fetch models — the provider may not expose a /models endpoint.');
      }
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRefreshingId(null);
    }
  };

  const setDefault = async (id: string) => {
    setBusyId(id);
    try {
      await endpoints.ai.providers.setDefault(id);
      flash('Default provider updated.');
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const toggleEnabled = async (p: AIProviderConfig) => {
    setBusyId(p.id);
    try {
      await endpoints.ai.providers.update(p.id, { enabled: !p.enabled });
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (p: AIProviderConfig) => {
    if (!confirmDelete(`provider "${p.name}"`)) return;
    setBusyId(p.id);
    try {
      await endpoints.ai.providers.remove(p.id);
      flash(`Provider "${p.name}" removed.`);
      if (editingId === p.id) setEditingId(null);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const editingProvider = providers.find((p) => p.id === editingId);
  const formModels = editingProvider?.models ?? [];

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>
          <span className="emoji">🧠</span> AI Providers
        </h2>
        <span className={`badge ${providers.length > 0 ? 'badge-success' : 'badge-muted'}`}>
          {providers.length > 0 ? `${providers.length} configured` : 'None configured'}
        </span>
      </div>

      <p className="panel-sub">
        Point the app at any model — local (Ollama, LM Studio, a custom URL on your machine) or
        cloud (OpenAI, Anthropic, Google). The active provider is used for every AI feature; the
        model override below applies to this provider only. Keys are stored on this machine and
        never sent back to the browser.
      </p>

      {error && <div className="notice notice-error">{error}</div>}
      {notice && <div className="notice notice-info">{notice}</div>}

      {loading ? (
        <div className="muted">Loading providers…</div>
      ) : providers.length === 0 ? (
        <div className="notice notice-info">
          No providers configured yet. Add one below — try{' '}
          <strong>Ollama</strong> (defaults to <code>http://localhost:11434/v1</code>) or a custom
          OpenAI-compatible endpoint.
        </div>
      ) : (
        <div className="ai-provider-list">
          {providers.map((p) => (
            <div key={p.id} className={`ai-provider-card${p.is_default ? ' is-default' : ''}${p.enabled ? '' : ' is-disabled'}`}>
              <div className="ai-provider-head">
                <div>
                  <strong>{p.name}</strong>{' '}
                  <span className={`badge ${p.is_local ? 'badge-info' : 'badge-muted'}`}>
                    {p.is_local ? 'Local' : 'Cloud'}
                  </span>
                  {p.is_default && <span className="badge badge-success">Default</span>}
                  {!p.enabled && <span className="badge badge-warning">Disabled</span>}
                </div>
                <div className="ai-provider-actions">
                  <button className="btn btn-sm" onClick={() => setDefault(p.id)} disabled={busyId === p.id || p.is_default} title="Use this provider for all AI features">
                    ⭐ Default
                  </button>
                  <button className="btn btn-sm" onClick={() => testConnection(p.id)} disabled={testingId === p.id}>
                    {testingId === p.id ? 'Testing…' : '🔌 Test'}
                  </button>
                  <button className="btn btn-sm" onClick={() => refreshModels(p.id)} disabled={refreshingId === p.id} title="Fetch the current model list">
                    {refreshingId === p.id ? 'Refreshing…' : '↻ Models'}
                  </button>
                  <button className="btn btn-sm" onClick={() => toggleEnabled(p)} disabled={busyId === p.id}>
                    {p.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button className="btn btn-sm" onClick={() => startEdit(p)}>✏️ Edit</button>
                  <button className="btn btn-sm btn-danger-ghost" onClick={() => remove(p)} disabled={busyId === p.id}>
                    🗑
                  </button>
                </div>
              </div>
              <div className="ai-provider-meta muted">
                {typeLabel(p.provider_type)} · {p.base_url || 'no base URL'}
                {p.model ? ` · model: ${p.model}` : ''}
                {p.has_api_key ? ` · key: ${p.api_key_preview}` : ' · no API key'}
              </div>
              {testResult?.id === p.id && (
                <div className={`notice ${testResult.result.ok ? 'notice-info' : 'notice-error'}`}>
                  {testResult.result.ok ? '✅ ' : '❌ '}
                  {testResult.result.message}
                  {testResult.result.latency_ms != null ? ` (${testResult.result.latency_ms}ms)` : ''}
                  {testResult.result.models && testResult.result.models.length > 0 ? (
                    <span className="muted"> — {testResult.result.models.length} models: {testResult.result.models.slice(0, 4).join(', ')}{testResult.result.models.length > 4 ? '…' : ''}</span>
                  ) : null}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <hr className="ai-provider-divider" />

      <h3 className="ai-provider-form-title">
        {editingId === null ? '➕ Add provider' : `✏️ Edit provider`}
      </h3>

      <div className="ai-provider-form">
        <div className="field-row">
          <label htmlFor="ai-provider-name">Name</label>
          <input
            id="ai-provider-name"
            type="text"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder="My Custom Model"
          />
        </div>

        <div className="field-row">
          <label htmlFor="ai-provider-type">Provider type</label>
          <select
            id="ai-provider-type"
            value={draft.provider_type}
            onChange={(e) => changeType(e.target.value as AIProviderType)}
          >
            {PROVIDER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field-row">
          <label htmlFor="ai-provider-url">Base URL</label>
          <input
            id="ai-provider-url"
            type="text"
            value={draft.base_url}
            onChange={(e) => setDraft({ ...draft, base_url: e.target.value })}
            placeholder="http://localhost:11434/v1"
            spellCheck={false}
          />
        </div>

        <div className="field-row">
          <label htmlFor="ai-provider-key">API key</label>
          <input
            id="ai-provider-key"
            type="password"
            value={draft.api_key}
            onChange={(e) => setDraft({ ...draft, api_key: e.target.value })}
            placeholder={editingId !== null ? 'Leave blank to keep the existing key' : 'Optional for local servers'}
            autoComplete="off"
          />
          {editingProvider?.has_api_key && (
            <span className="muted">stored: {editingProvider.api_key_preview}</span>
          )}
        </div>

        <div className="field-row">
          <label htmlFor="ai-provider-model">Model</label>
          <input
            id="ai-provider-model"
            type="text"
            value={draft.model}
            onChange={(e) => setDraft({ ...draft, model: e.target.value })}
            placeholder={formModels[0] ?? 'e.g. llama3, qwen3, gpt-4o, claude-3-7-sonnet'}
            list="ai-provider-models"
            spellCheck={false}
          />
          <datalist id="ai-provider-models">
            {formModels.map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
        </div>

        <div className="ai-provider-checks">
          <label className="ai-provider-check">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
            />
            Enabled
          </label>
          <label className="ai-provider-check">
            <input
              type="checkbox"
              checked={draft.is_default}
              onChange={(e) => setDraft({ ...draft, is_default: e.target.checked })}
            />
            Use as default model
          </label>
        </div>

        <div className="ai-provider-form-actions">
          <button className="btn btn-primary" onClick={() => void save()} disabled={saving}>
            {saving ? 'Saving…' : '💾 Save provider'}
          </button>
          <button className="btn btn-ghost" onClick={startAdd} disabled={saving || editingId === null}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
