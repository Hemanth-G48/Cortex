import { Component, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Fallback UI rendered when a child throws. May be a node or a render fn. */
  fallback: ReactNode | ((error: Error, reset: () => void) => ReactNode);
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

  render(): ReactNode {
    const { error } = this.state;
    if (error === null) return this.props.children;
    const { fallback } = this.props;
    return typeof fallback === 'function' ? fallback(error, this.reset) : fallback;
  }
}
