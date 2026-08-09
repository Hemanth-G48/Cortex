import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { endpoints } from '../../services/api';

interface Props {
  documentId: number;
  onFlash: (msg: string) => void;
}

const styles = {
  bar: {
    display: 'flex', gap: '0.4rem', flexWrap: 'wrap' as const,
    marginTop: '0.75rem', padding: '0.7rem 0.9rem',
    border: '1px dashed var(--border)', borderRadius: 'var(--radius-lg)',
    background: 'var(--bg-primary)',
  },
  hint: { fontSize: '0.68rem', color: 'var(--text-muted)', width: '100%', marginBottom: '0.1rem' },
};

export const NoteActions = ({ documentId, onFlash }: Props) => {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<string | null>(null);

  const makeQuiz = async () => {
    setBusy('quiz');
    try {
      const quiz = await endpoints.kb.quizzes.generate(documentId, 8, 'medium');
      onFlash(`Quiz #${quiz.id} generated from this note ✓`);
      navigate('/quiz');
    } catch (e) {
      onFlash(`Quiz failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const makeCards = async () => {
    setBusy('cards');
    try {
      const res = await endpoints.kb.flashcards.generate(documentId);
      onFlash(
        res.generated > 0
          ? `${res.generated} card candidate${res.generated === 1 ? '' : 's'} queued for review ✓`
          : 'No new cards — everything was already covered (or the note has no concepts)',
      );
    } catch (e) {
      onFlash(`Cards failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div style={styles.bar}>
      <span style={styles.hint}>Turn this note into study material (budget-capped AI generation):</span>
      <button type="button" className="btn btn-sm btn-primary" disabled={busy !== null} onClick={() => void makeQuiz()}>
        {busy === 'quiz' ? 'Generating…' : '🧠 Generate quiz'}
      </button>
      <button type="button" className="btn btn-sm btn-ghost" disabled={busy !== null} onClick={() => void makeCards()}>
        {busy === 'cards' ? 'Generating…' : '🃏 Generate flashcards'}
      </button>
      <button type="button" className="btn btn-sm btn-ghost" onClick={() => navigate('/flashcard-review')}>
        📥 Review queue
      </button>
    </div>
  );
};
