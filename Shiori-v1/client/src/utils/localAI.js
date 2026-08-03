// On-device AI — runs a small instruction-tuned model entirely in the browser
// via WebGPU (no API key, no server round-trip). The model weights are
// downloaded once and cached by the browser's Cache Storage (handled
// internally by @mlc-ai/web-llm), so every load after the first is instant
// and works fully offline.
import { create } from 'zustand'

const MODEL_ID = 'Llama-3.2-1B-Instruct-q4f16_1-MLC'

export const useLocalAIStore = create((set) => ({
  status: 'idle', // idle | loading | ready | unsupported | error
  progress: 0,
  progressText: '',
  error: null,
}))

export function isLocalAISupported() {
  return typeof navigator !== 'undefined' && !!navigator.gpu
}

let enginePromise = null

function loadEngine() {
  if (enginePromise) return enginePromise
  if (!isLocalAISupported()) {
    useLocalAIStore.setState({ status: 'unsupported' })
    return Promise.reject(new Error('WebGPU is not available in this browser'))
  }
  useLocalAIStore.setState({ status: 'loading', progress: 0, error: null })
  enginePromise = import('@mlc-ai/web-llm')
    .then(({ CreateMLCEngine }) => CreateMLCEngine(MODEL_ID, {
      initProgressCallback: (report) => {
        useLocalAIStore.setState({ progress: report.progress || 0, progressText: report.text || '' })
      },
    }))
    .then((engine) => {
      useLocalAIStore.setState({ status: 'ready', progress: 1 })
      return engine
    })
    .catch((e) => {
      enginePromise = null
      useLocalAIStore.setState({ status: 'error', error: e?.message || 'Failed to load the on-device model' })
      throw e
    })
  return enginePromise
}

// Kick off the download without blocking the caller — safe to call repeatedly.
export function preloadLocalAI() {
  if (!isLocalAISupported() || enginePromise) return
  loadEngine().catch(() => {})
}

export async function callLocalAI(prompt, { maxOutputTokens = 512, temperature = 0.7, system } = {}) {
  const engine = await loadEngine()
  const messages = []
  if (system) messages.push({ role: 'system', content: system })
  messages.push({ role: 'user', content: prompt })
  const reply = await engine.chat.completions.create({
    messages,
    temperature,
    max_tokens: maxOutputTokens,
  })
  return reply?.choices?.[0]?.message?.content?.trim() || null
}
