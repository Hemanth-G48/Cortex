import { useEffect, useMemo, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { endpoints } from '../services/api';
import type { Institution, Program, EnrollmentSummary } from '../services/api';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';

export const CompleteProfile = () => {
  const { isAuthenticated, loading: authLoading, refreshMe } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [institutions, setInstitutions] = useState<Institution[] | null>(null);
  const [programs, setPrograms] = useState<Program[] | null>(null);
  const [enrollment, setEnrollment] = useState<EnrollmentSummary | null>(null);
  const [instId, setInstId] = useState<number | null>(null);
  const [progId, setProgId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const currentInstId = enrollment?.institution_id ?? null;
  const currentProgId = enrollment?.program_id ?? null;

  useEffect(() => {
    if (!isAuthenticated) return;
    endpoints.curriculum.institutions().then(setInstitutions).catch(() => toast('Could not load institutions', 'error'));
    endpoints.enrollment.summary().then(setEnrollment).catch(() => undefined);
  }, [isAuthenticated, toast]);

  useEffect(() => {
    // Load programs for the freshly picked institution — or for the user's
    // current enrollment when they arrive already enrolled.
    const target = instId ?? currentInstId;
    if (target == null) return;
    setPrograms(null);
    setProgId(null);
    endpoints.curriculum.programs(target).then(setPrograms).catch(() => toast('Could not load programs', 'error'));
  }, [instId, currentInstId, toast]);

  const canSave = instId != null && progId != null;

  const handleSave = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      await endpoints.enrollment.update({ institution_id: instId, program_id: progId });
      await refreshMe();
      toast('Enrollment saved', 'success');
      navigate('/');
    } catch {
      toast('Could not save enrollment', 'error');
    } finally {
      setSaving(false);
    }
  };

  const selectedInstitution = useMemo(() => institutions?.find((i) => i.id === instId) ?? null, [institutions, instId]);

  if (authLoading) {
    return (
      <div className="page fade-in" style={{ maxWidth: 560, margin: '0 auto' }}>
        <Header title="Complete Profile" />
        <SkeletonCard />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="page fade-in" style={{ maxWidth: 560, margin: '0 auto' }}>
        <Header title="Complete Profile" />
        <EmptyState
          icon="🔐"
          title="Sign in to enroll"
          message="Log in or create an account to pick your institution and program."
          action={<Link className="btn btn-primary" to="/login">Go to login</Link>}
        />
      </div>
    );
  }

  return (
    <div className="page fade-in" style={{ maxWidth: 560, margin: '0 auto' }}>
      <Header title="Complete Profile" />

      {enrollment?.institution_name ? (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--success)' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Currently enrolled</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {enrollment.institution_name} · {enrollment.program_name} · {enrollment.subjects.length} subjects
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Pick a new institution/program below to switch.
          </div>
        </div>
      ) : (
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
          Choose your institution and program so the dashboard can show your curriculum, materials and quiz progress.
        </p>
      )}

      <div className="card" style={{ display: 'grid', gap: '1rem' }}>
        <label style={{ display: 'grid', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Institution</span>
          <select
            aria-label="Institution"
            value={instId ?? currentInstId ?? ''}
            onChange={(e) => setInstId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">— Select institution —</option>
            {institutions?.map((i) => (
              <option key={i.id} value={i.id}>{i.name} ({i.short_name})</option>
            ))}
          </select>
        </label>

        <label style={{ display: 'grid', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Program</span>
          <select
            aria-label="Program"
            value={progId ?? currentProgId ?? ''}
            onChange={(e) => setProgId(e.target.value ? Number(e.target.value) : null)}
            disabled={!selectedInstitution && !currentInstId}
          >
            <option value="">{instId != null && programs === null ? 'Loading programs…' : '— Select program —'}</option>
            {programs?.map((p) => (
              <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
            ))}
          </select>
        </label>

        {instId != null && programs !== null && programs.length === 0 && (
          <p style={{ fontSize: '0.75rem', color: 'var(--warning)' }}>No active programs for this institution yet.</p>
        )}

        <div className="modal-actions" style={{ justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={() => void handleSave()} disabled={!canSave || saving}>
            {saving ? 'Saving…' : 'Save enrollment'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CompleteProfile;
