/**
 * One owner for the destructive-action confirm policy.
 *
 * Every delete flow asks the same question with the same severity warning;
 * call sites only supply the noun phrase (e.g. 'this task').
 */
export const confirmDelete = (what: string): boolean =>
  window.confirm(`Delete ${what}? This cannot be undone.`);
