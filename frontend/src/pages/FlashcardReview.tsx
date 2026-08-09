import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { endpoints, type KbFlashcardCandidate } from '../services/api';

const styles = {
  card: {
    display: 'flex', gap: '0.75rem', alignItems: 'flex-start',
    padding: '1rem 1.1rem', marginBottom: '0.6rem',
  },
  q: { fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' },
  a: { fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem', whiteSpace: 'pre-wrap' as const },
  source: { fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.35rem' },
};

export const FlashcardReview = () => {
  const [items, setItems] = useState<KbFlashcardCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await endpoints.kb.flashcards.candidates('pending');
      setItems(res.items);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const flash = (msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 3000);
  };

  const review = async (approve: number[], reject: number[]) => {
    setBusy(true);
    try {
      const res = await endpoints.kb.flashcards.review({ approve, reject });
      flash(
        res.approved > 0
          ? `${res.approved} card${res.approved === 1 ? '' : 's'} added to the “From notes” deck ✓`
          : `${res.rejected} card${res.rejected === 1 ? '' : 's'} rejected`,
      );
      await load();
    } catch (e) {
      flash(`Review failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page-section">
      <Header title="Flashcard Review Queue" />

      {notice && (
        <div style={{
          padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '1rem',
          background: 'var(--accent-muted)', color: 'var(--text-primary)', fontSize: '0.85rem',
        }}>
          {notice}
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Loading candidates…</p>
      ) : items.length === 0 ? (
        <EmptyState
          icon="🃏"
          title="Nothing to review"
          message="Candidates appear here when you generate flashcards from a vault document. Approved cards land in the “From notes” deck."
          action={
            <Link className="btn btn-primary" to="/knowledge-base">Open Second Brain</Link>
          }
        />
      ) : (
        items.map((c) => (
          <div key={c.id} className="card" style={styles.card}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={styles.q}>{c.question}</div>
              <div style={styles.a}>{c.answer}</div>
              {c.document_title && (
                <div style={styles.source}>
                  📄 {c.document_title}
                  {c.source_chunk_id ? ` · chunk #${c.source_chunk_id}` : ''}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <button type="button" className="btn btn-sm btn-success" disabled={busy} onClick={() => void review([c.id], [])}>
                ✓ Approve
              </button>
              <button type="button" className="btn btn-sm btn-ghost" disabled={busy} onClick={() => void review([], [c.id])}>
                ✕ Reject
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
