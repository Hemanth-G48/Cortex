import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { endpoints } from '../services/api';

/**
 * Draft a ready-to-edit capture note for a gap, then jump straight to it in the
 * Second Brain (the `?doc=` deep link opens the document drawer).
 *
 * `noteBusy` is the name of the gap currently drafting (disables its buttons);
 * `noteError` surfaces failures inline without leaving the page.
 *
 * Lives in its own file so the gap-analysis component module only exports
 * components (keeps fast-refresh working).
 */
export const useGapNote = () => {
  const navigate = useNavigate();
  const [noteBusy, setNoteBusy] = useState<string | null>(null);
  const [noteError, setNoteError] = useState<string | null>(null);

  const clearNoteError = useCallback(() => setNoteError(null), []);

  const createNote = useCallback(async (
    gap: {
      name: string;
      why?: string | null;
      learn?: string[];
      practice?: string[];
      sources?: { document_id: number; title: string }[];
    },
    subject?: string | null,
  ) => {
    setNoteBusy(gap.name);
    setNoteError(null);
    try {
      const res = await endpoints.kb.gaps.createNote({
        name: gap.name,
        subject,
        why: gap.why ?? null,
        learn: gap.learn ?? [],
        practice: gap.practice ?? [],
        sources: (gap.sources ?? []).map((s) => ({ document_id: s.document_id, title: s.title })),
      });
      navigate(`/knowledge-base?doc=${res.document.id}`);
    } catch (e) {
      setNoteError((e as Error).message);
    } finally {
      // Safe even when navigation unmounts the page: the state update is
      // batched and the component simply never re-renders.
      setNoteBusy(null);
    }
  }, [navigate]);

  return { noteBusy, noteError, createNote, clearNoteError };
};
