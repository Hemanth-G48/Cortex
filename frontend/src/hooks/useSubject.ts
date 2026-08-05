import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';
import type { Subject, CurriculumUnit } from '../services/api';

export interface SubjectUnit extends CurriculumUnit {
  material_count: number;
}

/** Loads a subject plus its units, annotating each unit with a material count. */
export const useSubject = (subjectId: number) => {
  const [subject, setSubject] = useState<Subject | null>(null);
  const [units, setUnits] = useState<SubjectUnit[] | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const s = await endpoints.curriculum.subject(subjectId);
      setSubject(s);
      const rows = await endpoints.curriculum.units(subjectId);
      // Annotate each unit with its material count (catalog units don't carry one).
      const counts = await Promise.all(
        rows.map((u) => endpoints.materials.list(u.id, undefined, 1, 1).then((r) => r.total).catch(() => 0)),
      );
      setUnits(rows.map((u, i) => ({ ...u, material_count: counts[i] })));
    } catch {
      setError('Could not load this subject.');
    } finally {
      setLoading(false);
    }
  }, [subjectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { subject, units, loading, error, refresh };
};
