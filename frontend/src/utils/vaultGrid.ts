/** Vault grid column helpers (spec Change Grid, persisted to localStorage). */

export const GRID_COLS_KEY = 'vault-cols';
export const GRID_COLS_OPTIONS = [1, 2, 3, 4] as const;
export const DEFAULT_GRID_COLS = 3;

export function getGridCols(): number {
  try {
    const raw = Number(localStorage.getItem(GRID_COLS_KEY));
    if (GRID_COLS_OPTIONS.includes(raw as (typeof GRID_COLS_OPTIONS)[number])) return raw;
  } catch {
    /* localStorage unavailable */
  }
  return DEFAULT_GRID_COLS;
}

export function setGridCols(cols: number): void {
  try {
    localStorage.setItem(GRID_COLS_KEY, String(cols));
  } catch {
    /* localStorage unavailable */
  }
}
