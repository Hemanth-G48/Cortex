import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';
import type { CurriculumUnit, Subject, Material } from '../services/api';

interface UseUnitReturn {
  unit: CurriculumUnit | null;
  subject: Subject | null;
  materials: Material[];
  total: number;
  page: number;
  query: string;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  setQuery: (q: string) => void;
  setPage: (p: number) => void;
}

/** Loads a unit plus its subject (breadcrumb) and a paginated, searchable material list. */
export const useUnit = (unitId: number): UseUnitReturn => {
  const [unit, setUnit] = useState<CurriculumUnit | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [unitRow, matResp] = await Promise.all([
        endpoints.curriculum.unit(unitId),
        endpoints.materials.list(unitId, query || undefined, page, 20),
      ]);
      setUnit(unitRow);
      setMaterials(matResp.items);
      setTotal(matResp.total);
      if (unitRow) {
        endpoints.curriculum.subject(unitRow.subject_id).then(setSubject).catch(() => undefined);
      } else {
        setSubject(null);
      }
    } catch {
      setError('Could not load this unit.');
    } finally {
      setLoading(false);
    }
  }, [unitId, query, page]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { unit, subject, materials, total, page, query, loading, error, refresh, setQuery, setPage };
};
