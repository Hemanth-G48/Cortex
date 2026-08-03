import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('App', () => {
  it('renders without crashing', () => {
    const { container } = render(<App />);
    expect(container.querySelector('.app-shell')).toBeInTheDocument();
  });

  it('renders sidebar with Student OS logo', () => {
    render(<App />);
    expect(screen.getByText('🎓 Student OS')).toBeInTheDocument();
  });

  it('renders at least one navigation link', () => {
    render(<App />);
    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThanOrEqual(10);
  });
});
