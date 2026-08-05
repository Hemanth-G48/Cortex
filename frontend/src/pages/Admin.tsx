import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { useToast } from '../hooks/useToast';
import { endpoints } from '../services/api';
import type { Institution, Program, Subject, CurriculumUnit } from '../services/api';
import { InstitutionTable } from '../components/curriculum/InstitutionTable';
import { InstitutionForm } from '../components/curriculum/InstitutionForm';
import { ProgramForm } from '../components/curriculum/ProgramForm';
import { SubjectForm } from '../components/curriculum/SubjectForm';
import { UnitForm } from '../components/curriculum/UnitForm';
import { SkeletonTable } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';

export const Admin = () => {
  const { toast } = useToast();

  const [institutions, setInstitutions] = useState<Institution[] | null>(null);
  const [programs, setPrograms] = useState<Program[] | null>(null);
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [units, setUnits] = useState<CurriculumUnit[] | null>(null);

  const [instId, setInstId] = useState<number | null>(null);
  const [progId, setProgId] = useState<number | null>(null);
  const [subjId, setSubjId] = useState<number | null>(null);

  const loadInstitutions = useCallback(() => {
    endpoints.admin.allInstitutions().then(setInstitutions).catch(() => toast('Could not load institutions', 'error'));
  }, [toast]);

  useEffect(() => {
    loadInstitutions();
  }, [loadInstitutions]);

  useEffect(() => {
    if (instId == null) return;
    setPrograms(null);
    setProgId(null);
    setSubjects(null);
    setSubjId(null);
    setUnits(null);
    endpoints.curriculum.programs(instId).then(setPrograms).catch(() => toast('Could not load programs', 'error'));
  }, [instId, toast]);

  useEffect(() => {
    if (progId == null) return;
    setSubjects(null);
    setSubjId(null);
    setUnits(null);
    endpoints.curriculum.subjects(progId).then(setSubjects).catch(() => toast('Could not load subjects', 'error'));
  }, [progId, toast]);

  useEffect(() => {
    if (subjId == null) return;
    setUnits(null);
    endpoints.curriculum.units(subjId).then(setUnits).catch(() => toast('Could not load units', 'error'));
  }, [subjId, toast]);

  const refreshPrograms = useCallback(() => {
    if (instId == null) return;
    endpoints.curriculum.programs(instId).then(setPrograms).catch(() => toast('Could not load programs', 'error'));
  }, [instId, toast]);

  const refreshSubjects = useCallback(() => {
    if (progId == null) return;
    endpoints.curriculum.subjects(progId).then(setSubjects).catch(() => toast('Could not load subjects', 'error'));
  }, [progId, toast]);

  const refreshUnits = useCallback(() => {
    if (subjId == null) return;
    endpoints.curriculum.units(subjId).then(setUnits).catch(() => toast('Could not load units', 'error'));
  }, [subjId, toast]);

  const toggleInstitution = async (institution: Institution) => {
    try {
      const res = await endpoints.admin.toggleInstitution(institution.id);
      toast(res.is_active ? `${institution.name} approved` : `${institution.name} deactivated`, 'success');
      loadInstitutions();
    } catch {
      toast('Could not update status', 'error');
    }
  };

  return (
    <div className="fade-in">
      <Header title="Curriculum Admin" />
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
        Approve institutions and curate the catalog — programs, subjects and units.
      </p>

      {/* Institutions table */}
      <div className="page-section">
        <h2>Institutions</h2>
        {institutions === null ? (
          SkeletonTable(4)
        ) : institutions.length === 0 ? (
          <EmptyState icon="🏛️" title="No institutions yet" message="Create the first institution below." />
        ) : (
          <InstitutionTable institutions={institutions} onToggle={(i) => void toggleInstitution(i)} />
        )}
      </div>

      {/* Create institution */}
      <div className="page-section" style={{ maxWidth: 420 }}>
        <InstitutionForm onCreated={loadInstitutions} />
      </div>

      {/* Nested catalog creation */}
      <div className="page-section">
        <h2>Curate catalog</h2>
        <div className="curate-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', alignItems: 'start' }}>
          {/* Program */}
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Institution (for program)</span>
              <select aria-label="Institution for program" value={instId ?? ''} onChange={(e) => setInstId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">— Select —</option>
                {institutions?.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
            </label>
            {instId != null && <ProgramForm key={instId} institutionId={instId} onCreated={refreshPrograms} />}
          </div>

          {/* Subject */}
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Program (for subject)</span>
              <select aria-label="Program for subject" value={progId ?? ''} onChange={(e) => setProgId(e.target.value ? Number(e.target.value) : null)} disabled={!instId}>
                <option value="">{instId != null && programs === null ? 'Loading…' : '— Select —'}</option>
                {programs?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            {progId != null && <SubjectForm key={progId} programId={progId} onCreated={refreshSubjects} />}
          </div>

          {/* Unit */}
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Subject (for unit)</span>
              <select aria-label="Subject for unit" value={subjId ?? ''} onChange={(e) => setSubjId(e.target.value ? Number(e.target.value) : null)} disabled={!progId}>
                <option value="">{progId != null && subjects === null ? 'Loading…' : '— Select —'}</option>
                {subjects?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            {subjId != null && <UnitForm key={subjId} subjectId={subjId} onCreated={refreshUnits} />}
          </div>
        </div>
      </div>

      {/* Units preview */}
      {subjId != null && units !== null && units.length > 0 && (
        <div className="page-section">
          <h2>Units under subject</h2>
          <div className="card" style={{ display: 'grid', gap: '0.4rem' }}>
            {units.map((u) => (
              <div key={u.id} style={{ fontSize: '0.85rem' }}>
                <span className="badge" style={{ background: 'var(--bg-hover)', marginRight: '0.5rem' }}>Unit {u.unit_number}</span>
                {u.name}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Admin;
