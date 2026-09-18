import { Component, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface ErrorBoundaryProps {
  children: ReactNode;
  /**
   * Fallback UI rendered when a child throws. May be a node or a render fn.
   * Omit it to get the vault-aware default fallback (audit defect #99): the
   * error message, a Retry button, and a link to the Knowledge Base.
   */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** When this prop changes the boundary resets itself (e.g. route id / data key). */
  resetKey?: unknown;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render errors from a subtree so one failing component (e.g. the
 * knowledge-graph canvas) can never unmount the entire page. The fallback is
 * rendered in place of the crashed subtree; callers can offer a retry that
 * resets the boundary.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    // Reset when the boundary moves to a different subtree (new course/subject).
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      // Guarded by the resetKey change, so this is the canonical error-boundary
      // reset pattern (setState only fires when the key actually changed).
      // oxlint-disable-next-line react/no-did-update-set-state
      this.setState({ error: null });
    }
  }

  private reset = (): void => {
    this.setState({ error: null });
  };

  /**
   * Default fallback (defect #99): a crashed view is never a dead end — the
   * error text plus a retry that resets the boundary and a way back to the
   * vault. Rendered only when the caller supplied no `fallback`.
   */
  private renderDefaultFallback(error: Error): ReactNode {
    return (
      <div className="empty-state">
        <div className="empty-icon">⚠️</div>
        <div className="empty-title">Something went wrong</div>
        <div className="empty-message">{error.message || 'This panel failed to render.'}</div>
        <div className="empty-action" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
          <button type="button" className="btn btn-primary" onClick={this.reset}>
            Retry
          </button>
          <Link className="btn btn-ghost" to="/knowledge-base">
            View vault jobs
          </Link>
        </div>
      </div>
    );
  }

  render(): ReactNode {
    const { error } = this.state;
    if (error === null) return this.props.children;
    const { fallback } = this.props;
    if (fallback === undefined) return this.renderDefaultFallback(error);
    return typeof fallback === 'function' ? fallback(error, this.reset) : fallback;
  }
}
