/**
 * Detect a failed code-split chunk load (stale deploy, network blip) versus a
 * plain page render error.
 *
 * React.lazy caches a rejected dynamic import in its payload, so an error
 * boundary reset alone can never re-fetch a chunk that failed to load — the
 * only reliable recovery is a page reload. This helper distinguishes those
 * errors (which must reload) from render errors (where a state-preserving
 * boundary reset is the right recovery).
 *
 * Covers the known shapes:
 * - Vite dev + prod:  `TypeError: Failed to fetch dynamically imported module: ...`
 * - webpack:          `ChunkLoadError: Loading chunk N failed.`
 * - Safari/WebKit:    `Error: Importing a module script failed.`
 */
export function isChunkLoadError(error: Error): boolean {
  return (
    error.name === 'ChunkLoadError' ||
    /failed to fetch dynamically imported module|loading chunk .* failed|error loading dynamically imported module|importing a module script failed/i.test(
      error.message,
    )
  );
}
