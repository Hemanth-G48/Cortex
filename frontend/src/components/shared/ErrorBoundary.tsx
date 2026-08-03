import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="empty-state" style={{ padding: '3rem 1rem' }}>
          <div className="empty-icon">⚠️</div>
          <div className="empty-title">Something went wrong</div>
          <div className="empty-message" style={{ maxWidth: 400, margin: '0 auto' }}>
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </div>
          <button
            className="badge badge-info"
            style={{ cursor: 'pointer', border: 'none', padding: '0.4rem 1rem', marginTop: '1rem' }}
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
