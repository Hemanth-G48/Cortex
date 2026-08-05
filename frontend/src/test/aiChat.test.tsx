import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AIChat } from '../components/AIChat';

vi.mock('../services/api', () => {
  return {
    endpoints: {
      ai: {
        chat: vi.fn().mockResolvedValue({
          message: 'You have 3 pending assignments. Want a study plan?',
          should_generate_plan: false,
          ai_used: false,
        }),
      },
    },
  };
});

describe('AIChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts collapsed and opens on the FAB click', () => {
    render(<AIChat />);
    expect(screen.getByLabelText('Open AI assistant')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Open AI assistant'));
    expect(screen.getByText('Shiori Assistant')).toBeInTheDocument();
    expect(screen.getByText(/Hey! I'm Shiori/)).toBeInTheDocument();
  });

  it('sends a message and renders the AI reply', async () => {
    render(<AIChat />);
    fireEvent.click(screen.getByLabelText('Open AI assistant'));

    const input = screen.getByPlaceholderText('Ask about your study life…');
    fireEvent.change(input, { target: { value: 'What are my deadlines?' } });
    fireEvent.click(screen.getByText('➤'));

    await waitFor(() => expect(screen.getByText(/3 pending assignments/)).toBeInTheDocument());
    // The user's message should appear in the thread
    expect(screen.getByText('What are my deadlines?')).toBeInTheDocument();
  });

  it('sends a quick prompt chip', async () => {
    render(<AIChat />);
    fireEvent.click(screen.getByLabelText('Open AI assistant'));

    fireEvent.click(screen.getByText('Help'));
    await waitFor(() => expect(screen.getByText(/3 pending assignments/)).toBeInTheDocument());
  });
});
