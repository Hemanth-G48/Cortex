import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Institution, Program, Subject } from '../services/api';
import { InstitutionCard } from '../components/curriculum/InstitutionCard';
import { ProgramCard } from '../components/curriculum/ProgramCard';
import { SemesterGroup } from '../components/curriculum/SemesterGroup';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';

export const Browse = () => {
  const navigate = useNavigate();

  const [institutions, setInstitutions] = useState<Institution[] | null>(null);
  const [programs, setPrograms] = useState<Program[] | null>(null);
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [instId, setInstId] = useState<number | null>(null);
  const [progId, setProgId] = useState<number | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    endpoints.curriculum
      .institutions()
      .then((rows) => {
        setInstitutions(rows);
        if (rows.length === 1) setInstId(rows[0].id);
      })
      .catch(() => setError('Could not load institutions.'));
  }, []);

  useEffect(() => {
    if (instId == null) return;
    let stale = false;
    setPrograms(null);
    setSubjects(null);
    setProgId(null);
    endpoints.curriculum
      .programs(instId)
      .then((rows) => {
        if (stale) return;
        setPrograms(rows);
        if (rows.length === 1) setProgId(rows[0].id);
      })
      .catch(() => !stale && setError('Could not load programs.'));
    return () => {
      stale = true;
    };
  }, [instId]);

  useEffect(() => {
    if (progId == null) return;
    let stale = false;
    setSubjects(null);
    endpoints.curriculum
      .subjects(progId)
      .then((rows) => !stale && setSubjects(rows))
      .catch(() => !stale && setError('Could not load subjects.'));
    return () => {
      stale = true;
    };
  }, [progId]);

  const selectedInstitution = useMemo(
    () => institutions?.find((i) => i.id === instId) ?? null,
    [institutions, instId],
  );
  const selectedProgram = useMemo(() => programs?.find((p) => p.id === progId) ?? null, [programs, progId]);

  const semesterGroups = useMemo(() => {
    if (!subjects) return [];
    const groups = new Map<string, Subject[]>();
    for (const s of subjects) {
      const key = s.semester != null ? `Semester ${s.semester}` : 'Other';
      groups.set(key, [...(groups.get(key) ?? []), s]);
    }
    return [...groups.entries()];
  }, [subjects]);

  return (
    <div className="fade-in">
      <Header title="Browse Curriculum" />
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
        Explore institutions, programs and subjects from the public catalog — then dive into units, materials, summaries and quizzes.
      </p>

      {error && <div className="card" style={{ borderColor: 'var(--danger)', color: 'var(--danger)', marginBottom: '1rem' }}>{error}</div>}

      <div className="browse-cascade" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem', alignItems: 'start' }}>
        {/* Level 1 — Institutions */}
        <section aria-label="Institutions">
          <h3 className="browse-level-label">1 · Institution</h3>
          {institutions === null ? (
            <div style={{ display: 'grid', gap: '0.75rem' }}><SkeletonCard /><SkeletonCard /></div>
          ) : institutions.length === 0 ? (
            <EmptyState icon="🏛️" title="No institutions yet" message="The catalog is empty — check back soon." />
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {institutions.map((i) => (
                <InstitutionCard key={i.id} institution={i} selected={i.id === instId} onClick={() => setInstId(i.id)} />
              ))}
            </div>
          )}
        </section>

        {/* Level 2 — Programs */}
        <section aria-label="Programs">
          <h3 className="browse-level-label">2 · Program</h3>
          {!selectedInstitution ? (
            <EmptyState icon="👈" title="Pick an institution" message="Programs appear here once you select one." />
          ) : programs === null ? (
            <div style={{ display: 'grid', gap: '0.75rem' }}><SkeletonCard /></div>
          ) : programs.length === 0 ? (
            <EmptyState icon="🎓" title="No programs" message="This institution has no active programs yet." />
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {programs.map((p) => (
                <ProgramCard key={p.id} program={p} selected={p.id === progId} onClick={() => setProgId(p.id)} />
              ))}
            </div>
          )}
        </section>

        {/* Level 3 — Subjects by semester */}
        <section aria-label="Subjects">
          <h3 className="browse-level-label">3 · Subjects</h3>
          {!selectedProgram ? (
            <EmptyState icon="👈" title="Pick a program" message="Semester-grouped subjects appear here once you select one." />
          ) : subjects === null ? (
            <div style={{ display: 'grid', gap: '0.75rem' }}><SkeletonCard /><SkeletonCard /></div>
          ) : subjects.length === 0 ? (
            <EmptyState icon="📘" title="No subjects" message="This program has no subjects yet." />
          ) : (
            semesterGroups.map(([label, groupSubjects]) => (
              <SemesterGroup key={label} label={label} subjects={groupSubjects} onOpenSubject={(id) => navigate(`/subjects/${id}`)} />
            ))
          )}
        </section>
      </div>
    </div>
  );
};

export default Browse;
