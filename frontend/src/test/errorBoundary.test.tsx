import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '../components/shared/ErrorBoundary';

const Boom = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error('boom');
  return <div>fine</div>;
};

describe('ErrorBoundary', () => {
  it('renders children when nothing throws', () => {
    render(
      <ErrorBoundary fallback={<div>fallback</div>}>
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('fine')).toBeInTheDocument();
  });

  it('renders the fallback when a child throws — page is NOT blank', () => {
    render(
      <ErrorBoundary fallback={<div>graph failed to render</div>}>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByText('graph failed to render')).toBeInTheDocument();
    expect(screen.queryByText('boom')).not.toBeInTheDocument();
  });

  it('supports a render-fn fallback with a working reset', () => {
    const { rerender } = render(
      <ErrorBoundary fallback={(_, reset) => <button onClick={reset}>try again</button>}>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByRole('button', { name: 'try again' })).toBeInTheDocument();
    // The failing child is fixed, then the user clicks retry — the boundary
    // must render the child again instead of staying stuck on the fallback.
    rerender(
      <ErrorBoundary fallback={(_, reset) => <button onClick={reset}>try again</button>}>
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'try again' }));
    expect(screen.getByText('fine')).toBeInTheDocument();
  });

  it('auto-resets when resetKey changes (navigating to another course)', () => {
    const { rerender } = render(
      <ErrorBoundary resetKey={1} fallback={<div>oops</div>}>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByText('oops')).toBeInTheDocument();
    rerender(
      <ErrorBoundary resetKey={2} fallback={<div>oops</div>}>
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('fine')).toBeInTheDocument();
  });
});
