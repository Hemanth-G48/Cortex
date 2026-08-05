import { endpoints } from '../services/api';

/**
 * Frontend AI helpers (99-phase plan, Phase 6).
 *
 * Mirrors Shiori-v1's `utils/ai.js` API (`aiAvailable`, `aiModeLabel`,
 * `generateAI`) but resolves capability from the backend `/api/ai/health`
 * endpoint instead of a browser-local model, since the provider lives
 * server-side (OmniRoute).
 */

export interface GenerateOptions {
  maxTokens?: number;
  temperature?: number;
}

/** True when the backend reports an AI provider is configured + enabled. */
export async function aiAvailable(): Promise<boolean> {
  try {
    const health = await endpoints.ai.health();
    return health.available;
  } catch {
    return false;
  }
}

/** Human label for the current AI mode ('AI · <model>' or 'Offline'). */
export async function aiModeLabel(): Promise<string> {
  try {
    const health = await endpoints.ai.health();
    return health.available && health.model ? `AI · ${health.model}` : 'Offline';
  } catch {
    return 'Offline';
  }
}

/**
 * Run a prompt through the backend AI complete endpoint.
 * Returns the model text, or null when AI is unavailable/failed — callers
 * fall back to deterministic demo content, mirroring Shiori's behavior.
 */
const AI_MODEL_KEY = 'slos-ai-model';

/** Model override chosen in Settings (empty string = backend default). */
export function selectedModel(): string {
  try {
    return localStorage.getItem(AI_MODEL_KEY) ?? '';
  } catch {
    return '';
  }
}

export async function generateAI(prompt: string, opts: GenerateOptions = {}): Promise<string | null> {
  try {
    const model = selectedModel() || undefined;
    const res = await endpoints.ai.complete({
      prompt,
      max_tokens: opts.maxTokens,
      temperature: opts.temperature,
      model,
    });
    return res.text;
  } catch {
    return null;
  }
}
