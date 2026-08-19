/**
 * Suspense fallback shown while a code-split route chunk loads. Reuses the
 * theme's CSS variables so it matches whatever palette is active.
 */
export function PageLoader({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="page-loader" role="status" aria-live="polite">
      <span className="page-loader-spinner" aria-hidden="true" />
      <span className="page-loader-label">{label}</span>
    </div>
  );
}
