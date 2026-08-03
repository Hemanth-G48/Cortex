// Unified AI entrypoint — tries the user's Gemini key first (fastest, best
// quality), then falls back to the on-device WebGPU model so every AI
// feature works with zero setup and zero API key.
import { callGeminiClient, hasClientKey } from './gemini'
import { callLocalAI, isLocalAISupported, useLocalAIStore } from './localAI'

export function aiAvailable() {
  return hasClientKey() || isLocalAISupported()
}

export function aiModeLabel() {
  if (hasClientKey()) return 'Gemini'
  if (isLocalAISupported()) return 'On-device AI'
  return 'Offline'
}

export async function generateAI(prompt, opts = {}) {
  if (hasClientKey()) {
    const result = await callGeminiClient(prompt, opts).catch(() => null)
    if (result) return result
  }
  if (isLocalAISupported()) {
    try {
      return await callLocalAI(prompt, opts)
    } catch {
      return null
    }
  }
  return null
}

export { useLocalAIStore, isLocalAISupported }
