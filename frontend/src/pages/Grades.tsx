import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Header } from '../components/layout/Header';
import { GradeTrendChart } from '../components/grades/GradeTrendChart';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import type { Course, CourseWeight, GPAResponse, Grade, KbMastery } from '../services/api';

const EMPTY_COURSE = { title: '', credits: 3 };
const EMPTY_GRADE = { course_id: 0, title: '', points_earned: '', points_possible: '', category_id: '' };

const letterColor = (letter: string | null) => {
  if (!letter) return 'var(--text-muted)';
  if (letter.startsWith('A')) return 'var(--success)';
  if (letter.startsWith('B')) return 'var(--info)';
  if (letter.startsWith('C')) return 'var(--warning)';
  return 'var(--danger)';
};

const gpaColor = (gpa: number | null) => {
  if (gpa === null) return 'var(--text-muted)';
  if (gpa >= 3.5) return 'var(--success)';
  if (gpa >= 3.0) return 'var(--warning)';
  return 'var(--danger)';
};

export const Grades = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [gpaData, setGpaData] = useState<GPAResponse | null>(null);
  const [allGrades, setAllGrades] = useState<Grade[]>([]);
  // Defect #71: vault-derived competency shown beside the GPA.
  const [vaultMastery, setVaultMastery] = useState<KbMastery | null>(null);
  const [weights, setWeights] = useState<Record<number, CourseWeight[]>>({});
  const [needed, setNeeded] = useState<number | null>(null);

  const [showAddCourse, setShowAddCourse] = useState(false);
  const [showAddGrade, setShowAddGrade] = useState(false);
  const [showWeights, setShowWeights] = useState(false);
  const [courseForm, setCourseForm] = useState(EMPTY_COURSE);
  const [gradeForm, setGradeForm] = useState(EMPTY_GRADE);

  const [finalWeight, setFinalWeight] = useState(30);
  const [desiredGrade, setDesiredGrade] = useState(90);
  const [currentPct, setCurrentPct] = useState(85);

  const [trendCourse, setTrendCourse] = useState<number | null>(null);
  const [newWeight, setNewWeight] = useState({ name: '', weight: '' });

  const refresh = useCallback(async () => {
    try {
      const [cs, gpa, grs, mastery] = await Promise.all([
        endpoints.courses.list(),
        endpoints.grades.gpa(),
        endpoints.grades.list(),
        endpoints.kb.mastery().catch(() => null),
      ]);
      setCourses(cs);
      setGpaData(gpa);
      setAllGrades(grs);
      setVaultMastery(mastery);
      if (trendCourse === null && gpa.courses.length > 0) {
        setTrendCourse(gpa.courses[0].course_id);
      }
      // Load weights for courses that have them.
      const wMap: Record<number, CourseWeight[]> = {};
      await Promise.all(
        gpa.courses.map(async (c) => {
          try {
            wMap[c.course_id] = await endpoints.grades.weights(c.course_id);
          } catch {
            /* no weights */
          }
        }),
      );
      // Defect #70: courses with no weights yet are seeded from the enrolled
      // curriculum's credit hours (GET /enrollment/summary) — the real
      // weighting factor the curriculum records — rather than starting empty.
      const missing = gpa.courses.filter((c) => (wMap[c.course_id] ?? []).length === 0);
      if (missing.length > 0) {
        const enrollmentSummary = await endpoints.enrollment.summary().catch(() => null);
        const subjects = enrollmentSummary?.subjects ?? [];
        const totalCredits = subjects.reduce((s, sub) => s + (sub.credits ?? 0), 0);
        if (totalCredits > 0) {
          await Promise.all(
            missing.map(async (c) => {
              const title = c.title.trim().toLowerCase();
              const subject =
                subjects.find((s) => s.name.trim().toLowerCase() === title) ??
                subjects.find((s) => title.includes(s.name.trim().toLowerCase()));
              if (!subject) return;
              const share = Math.round(((subject.credits ?? 0) / totalCredits) * 100);
              if (share <= 0) return;
              try {
                const created = await endpoints.grades.createWeight({
                  course_id: c.course_id,
                  name: `${subject.name} (curriculum credits)`,
                  weight: share,
                });
                wMap[c.course_id] = [created];
              } catch {
                /* leave the course without weights */
              }
            }),
          );
        }
      }
      setWeights(wMap);
    } catch {
      /* silent */
    }
  }, [trendCourse]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Defect #42 fix: the predictor is debounced (300ms) so typing doesn't
  // fire an API request per keystroke.
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [debounced, setDebounced] = useState({ currentPct, finalWeight, desiredGrade });

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebounced({ currentPct, finalWeight, desiredGrade });
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [currentPct, finalWeight, desiredGrade]);

  useEffect(() => {
    endpoints.grades.neededOnFinal({
      current_pct: debounced.currentPct,
      final_weight_pct: debounced.finalWeight,
      desired_pct: debounced.desiredGrade,
    })
      .then((res) => setNeeded(res.needed_pct))
      .catch(() => setNeeded(null));
  }, [debounced]);

  // Defect #43 fix: delete a grade entry.
  const handleDeleteGrade = async (gradeId: number) => {
    if (!confirmDelete('this grade entry')) return;
    try {
      await endpoints.grades.delete(gradeId);
      void refresh();
    } catch {
      /* non-fatal: refresh keeps current view */
    }
  };

  const gradedCount = gpaData?.courses.filter((c) => c.percentage !== null).length ?? 0;

  const handleAddCourse = async () => {
    if (!courseForm.title.trim()) return;
    try {
      await endpoints.courses.create({ title: courseForm.title.trim(), credits: Number(courseForm.credits) || 3 });
      setCourseForm(EMPTY_COURSE);
      setShowAddCourse(false);
      void refresh();
    } catch {
      /* silent */
    }
  };

  const openAddGrade = (courseId?: number) => {
    setGradeForm({ ...EMPTY_GRADE, course_id: courseId ?? courses[0]?.id ?? 0 });
    setShowAddGrade(true);
  };

  const handleAddGrade = async () => {
    const earned = Number(gradeForm.points_earned);
    const possible = Number(gradeForm.points_possible);
    if (!gradeForm.course_id || !possible || Number.isNaN(earned) || Number.isNaN(possible)) return;
    try {
      await endpoints.grades.create({
        course_id: Number(gradeForm.course_id),
        title: gradeForm.title.trim() || 'Assignment',
        points_earned: earned,
        points_possible: possible,
        category_id: gradeForm.category_id ? Number(gradeForm.category_id) : null,
      });
      setGradeForm(EMPTY_GRADE);
      setShowAddGrade(false);
      void refresh();
    } catch {
      /* silent */
    }
  };

  const openWeights = (courseId: number) => {
    setGradeForm((f) => ({ ...f, course_id: courseId }));
    setNewWeight({ name: '', weight: '' });
    setShowWeights(true);
  };

  const handleAddWeight = async () => {
    if (!gradeForm.course_id || !newWeight.name.trim()) return;
    try {
      await endpoints.grades.createWeight({
        course_id: Number(gradeForm.course_id),
        name: newWeight.name.trim(),
        weight: Number(newWeight.weight) || 0,
      });
      setNewWeight({ name: '', weight: '' });
      void refresh();
    } catch {
      /* silent */
    }
  };

  const handleDeleteWeight = async (id: number) => {
    try {
      await endpoints.grades.deleteWeight(id);
      void refresh();
    } catch {
      /* silent */
    }
  };

  const trendGrades = useMemo(() => {
    if (trendCourse === null) return [];
    return allGrades.filter((g) => g.course_id === trendCourse);
  }, [trendCourse, allGrades]);

  const activeCourse = useMemo(
    () => gpaData?.courses.find((c) => c.course_id === trendCourse) ?? null,
    [gpaData, trendCourse],
  );

  const gpa = gpaData?.gpa ?? null;

  return (
    <div className="fade-in">
      <Header title="Grades" />
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <button type="button" className="btn btn-ghost" onClick={() => openAddGrade()} disabled={courses.length === 0}>
          ＋ Add Grade
        </button>
        <button type="button" className="btn btn-primary" onClick={() => setShowAddCourse(true)}>
          ＋ Add Course
        </button>
      </div>

      {/* GPA overview */}
      <div
        className="card"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1.5rem',
          flexWrap: 'wrap',
          borderLeft: `3px solid ${gpaColor(gpa)}`,
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <div className="widget-title">Cumulative GPA</div>
          <div
            style={{
              fontSize: '3rem',
              fontWeight: 700,
              lineHeight: 1,
              color: gpaColor(gpa),
              textShadow: gpa !== null ? `0 0 24px ${gpaColor(gpa)}44` : 'none',
            }}
          >
            {gpa !== null ? gpa.toFixed(2) : '—'}
          </div>
        </div>
        <div style={{ height: 56, width: 1, background: 'var(--border)' }} />
        <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          <div>
            Tracking <strong style={{ color: 'var(--text-primary)' }}>{gradedCount}</strong> courses with grades
          </div>
          <div style={{ marginTop: '0.25rem' }}>
            Out of <strong style={{ color: 'var(--text-primary)' }}>{courses.length}</strong> total courses
          </div>
          {/* Defect #71: the vault's practice-derived competency beside the
              recorded GPA, so both signals are visible together. */}
          {vaultMastery && vaultMastery.topics_total > 0 && (
            <div style={{ marginTop: '0.25rem' }}>
              Vault mastery{' '}
              <strong style={{ color: 'var(--text-primary)' }}>{vaultMastery.score_pct}%</strong>
              {' '}across {vaultMastery.topics_total} topics · {vaultMastery.hours_logged}h logged
            </div>
          )}
        </div>
      </div>

      {/* Course grid */}
      {gpaData && gpaData.courses.length > 0 ? (
        <div className="card-grid" style={{ marginBottom: '1.5rem' }}>
          {gpaData.courses.map((c) => {
            const color = letterColor(c.letter_grade);
            return (
              <div
                key={c.course_id}
                className="card"
                style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', cursor: 'pointer' }}
                onClick={() => setTrendCourse(c.course_id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setTrendCourse(c.course_id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{c.title}</div>
                  <span style={{ fontFamily: 'monospace', fontSize: '1.35rem', fontWeight: 700, color, textShadow: `0 0 12px ${color}55` }}>
                    {c.letter_grade ?? '—'}
                  </span>
                </div>
                <div style={{ height: 5, background: 'var(--bg-hover)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(c.percentage ?? 0, 100)}%`,
                      background: color,
                      borderRadius: 3,
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {c.percentage !== null ? `${c.percentage}%` : 'No grades yet'}
                  {c.credits ? ` · ${c.credits} credits` : ''}
                  {c.percentage !== null ? ` · GPA ${(c.gpa ?? 0).toFixed(1)}` : ''}
                </div>
                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      openAddGrade(c.course_id);
                    }}
                  >
                    ＋ Grade
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      openWeights(c.course_id);
                    }}
                  >
                    ⚖ Weights
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card empty-state" style={{ marginBottom: '1.5rem' }}>
          <div className="empty-icon">📊</div>
          <div className="empty-title">No courses yet</div>
          <div className="empty-message">Add a course and some grades to see your GPA here.</div>
          <div className="empty-action">
            <button type="button" className="btn btn-primary" onClick={() => setShowAddCourse(true)}>
              Add Course
            </button>
          </div>
        </div>
      )}

      {/* Trend chart */}
      {activeCourse && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h2 className="widget-title" style={{ margin: 0 }}>Grade Trend — {activeCourse.title}</h2>
            <select
              value={trendCourse ?? ''}
              onChange={(e) => setTrendCourse(Number(e.target.value))}
              style={{ width: 'auto', fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}
            >
              {gpaData?.courses.map((c) => (
                <option key={c.course_id} value={c.course_id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>
          <GradeTrendChart grades={trendGrades} height={110} />
          {/* Defect #43 fix: per-grade delete. */}
          {trendGrades.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.75rem' }}>
              {trendGrades.map((g) => (
                <div
                  key={g.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '0.5rem',
                    padding: '0.4rem 0.6rem',
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.78rem',
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.title}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                    <span className="badge badge-info">{g.points_earned}/{g.points_possible}</span>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      style={{ color: 'var(--danger)' }}
                      onClick={() => void handleDeleteGrade(g.id)}
                      aria-label={`Delete ${g.title}`}
                    >
                      ✕
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Grade predictor */}
      <div className="card">
        <h2 className="widget-title" style={{ marginBottom: '0.5rem' }}>🧮 Grade Predictor</h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          What grade do I need on the final exam?
        </p>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          {[
            { label: 'Current Grade (%)', val: currentPct, set: setCurrentPct },
            { label: 'Final Exam Weight (%)', val: finalWeight, set: setFinalWeight },
            { label: 'Desired Final Grade (%)', val: desiredGrade, set: setDesiredGrade },
          ].map(({ label, val, set }) => (
            <div key={label} style={{ flex: 1, minWidth: 150 }}>
              <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.35rem', fontWeight: 600 }}>
                {label}
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={val}
                onChange={(e) => set(Number(e.target.value))}
                style={{ width: '100%', fontWeight: 600 }}
              />
            </div>
          ))}
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            flexWrap: 'wrap',
            padding: '1rem 1.25rem',
            background: 'var(--bg-primary)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
          }}
        >
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>You need at least</span>
          <span
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: needed !== null && needed > 100 ? 'var(--danger)' : needed !== null && needed < 60 ? 'var(--success)' : 'var(--info)',
            }}
          >
            {needed !== null ? `${needed.toFixed(1)}%` : '—'}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>on your final exam.</span>
          {needed !== null && needed > 100 && (
            <span className="badge badge-danger">Not achievable — aim higher now!</span>
          )}
        </div>
      </div>

      {/* Add Course modal */}
      {showAddCourse && (
        <div className="modal-overlay" onClick={() => setShowAddCourse(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Add Course</h2>
            <label className="modal-field" style={{ justifyContent: 'flex-start' }}>
              <span style={{ width: 90 }}>Course name</span>
              <input
                value={courseForm.title}
                onChange={(e) => setCourseForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="e.g. AP Biology"
                onKeyDown={(e) => e.key === 'Enter' && void handleAddCourse()}
                style={{ flex: 1, width: 'auto' }}
              />
            </label>
            <label className="modal-field">
              <span>Credits</span>
              <input
                type="number"
                min={0}
                step={0.5}
                value={courseForm.credits}
                onChange={(e) => setCourseForm((f) => ({ ...f, credits: Number(e.target.value) }))}
              />
            </label>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowAddCourse(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={() => void handleAddCourse()}>Add Course</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Grade modal */}
      {showAddGrade && (
        <div className="modal-overlay" onClick={() => setShowAddGrade(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Add Grade</h2>
            <div style={{ marginBottom: '0.75rem' }}>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', display: 'block', fontWeight: 600 }}>Course</label>
              <select
                value={gradeForm.course_id}
                onChange={(e) => setGradeForm((f) => ({ ...f, course_id: Number(e.target.value) }))}
                style={{ width: '100%' }}
              >
                <option value={0} disabled>Select course</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>
            </div>
            <div style={{ marginBottom: '0.75rem' }}>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', display: 'block', fontWeight: 600 }}>Assignment name</label>
              <input
                value={gradeForm.title}
                onChange={(e) => setGradeForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Midterm Exam"
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', display: 'block', fontWeight: 600 }}>Points earned</label>
                <input
                  type="number"
                  min={0}
                  value={gradeForm.points_earned}
                  onChange={(e) => setGradeForm((f) => ({ ...f, points_earned: e.target.value }))}
                  style={{ width: '100%', fontWeight: 600 }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', display: 'block', fontWeight: 600 }}>Points possible</label>
                <input
                  type="number"
                  min={0}
                  value={gradeForm.points_possible}
                  onChange={(e) => setGradeForm((f) => ({ ...f, points_possible: e.target.value }))}
                  style={{ width: '100%', fontWeight: 600 }}
                />
              </div>
            </div>
            {(weights[gradeForm.course_id]?.length ?? 0) > 0 && (
              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', display: 'block', fontWeight: 600 }}>Category (optional)</label>
                <select
                  value={gradeForm.category_id}
                  onChange={(e) => setGradeForm((f) => ({ ...f, category_id: e.target.value }))}
                  style={{ width: '100%' }}
                >
                  <option value="">— Uncategorized —</option>
                  {weights[gradeForm.course_id]?.map((w) => (
                    <option key={w.id} value={w.id}>{w.name} ({w.weight}%)</option>
                  ))}
                </select>
              </div>
            )}
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowAddGrade(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={() => void handleAddGrade()}>Add Grade</button>
            </div>
          </div>
        </div>
      )}

      {/* Weights modal */}
      {showWeights && (
        <div className="modal-overlay" onClick={() => setShowWeights(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Weighted Categories</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              {gpaData?.courses.find((c) => c.course_id === gradeForm.course_id)?.title ?? 'Course'} — categories with %
            </p>
            {(weights[gradeForm.course_id] ?? []).length === 0 ? (
              <div className="empty-state" style={{ padding: '1rem' }}>
                <div className="empty-message">No weighted categories — grades are averaged as points.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.75rem' }}>
                {(weights[gradeForm.course_id] ?? []).map((w) => (
                  <div
                    key={w.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '0.5rem',
                      padding: '0.5rem 0.75rem',
                      background: 'var(--bg-primary)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <span>{w.name}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className="badge badge-info">{w.weight}%</span>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        style={{ color: 'var(--danger)' }}
                        onClick={() => void handleDeleteWeight(w.id)}
                      >
                        ✕
                      </button>
                    </span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <input
                value={newWeight.name}
                onChange={(e) => setNewWeight((w) => ({ ...w, name: e.target.value }))}
                placeholder="Category name"
                style={{ flex: 1 }}
              />
              <input
                type="number"
                min={0}
                max={100}
                value={newWeight.weight}
                onChange={(e) => setNewWeight((w) => ({ ...w, weight: e.target.value }))}
                placeholder="%"
                style={{ width: 64 }}
              />
              <button type="button" className="btn btn-primary" onClick={() => void handleAddWeight()}>
                Add
              </button>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowWeights(false)}>Done</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
