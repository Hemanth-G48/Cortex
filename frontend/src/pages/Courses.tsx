import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Course, CourseSyncStatus } from '../services/api';
import { CourseCardsGrid } from '../components/courses/CourseCardsGrid';
import { AcademicResourcesGrid } from '../components/resources/AcademicResourcesGrid';

const formatTime = (iso?: string | null) => {
  if (!iso) return 'never';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? 'unknown' : d.toLocaleString();
};

export const Courses = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [status, setStatus] = useState<CourseSyncStatus | null>(null);
  const [syncing, setSyncing] = useState<'kb' | 'classroom' | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(() => {
    endpoints.courses.list().then(setCourses).catch(() => {});
    endpoints.courses.syncStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(load, [load]);

  const syncKb = async () => {
    setSyncing('kb');
    setMessage(null);
    try {
      const res = await endpoints.courses.syncKb();
      const extra =
        res.course_tags === 0 && res.course_folders === 0
          ? ' No subjects found yet — tag a note with `course:<name>` or keep notes in top-level vault folders.'
          : '';
      setMessage(`Second Brain synced — ${res.created} created, ${res.updated} updated, ${res.removed} removed${res.course_folders > 0 ? ` (${res.course_folders} from folders)` : ''}.${extra}`);
      load();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setSyncing(null);
    }
  };

  const syncClassroom = async () => {
    setSyncing('classroom');
    setMessage(null);
    try {
      const res = await endpoints.classroom.courses();
      const suffix = res.source === 'mock' ? ' (offline demo — connect Google for live courses)' : '';
      setMessage(`Google Classroom synced — ${res.courses.length} course(s) imported${suffix}.`);
      load();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setSyncing(null);
    }
  };

  const inProgress = courses.filter((c) => c.status === 'In progress' || c.status === 'Not started');
  const completed = courses.filter((c) => c.status === 'Completed');

  // Group by origin so Second Brain subjects are a single clearly-visible set.
  // The filters are mutually exclusive so one course can never appear twice.
  const isKb = (c: Course) =>
    c.source_type === 'kb_tag' || c.source_type === 'kb_folder' || !!c.kb_tag_id;
  const isClassroom = (c: Course) => c.source_type === 'classroom';
  // Active subjects first (In progress / Not started), then completed, then title.
  const statusRank = (c: Course) => (c.status === 'Completed' ? 1 : 0);
  const byStatusThenTitle = (a: Course, b: Course) =>
    statusRank(a) - statusRank(b) || a.title.localeCompare(b.title);
  const kbCourses = courses.filter((c) => isKb(c) && !isClassroom(c)).sort(byStatusThenTitle);
  const classroomCourses = courses.filter((c) => isClassroom(c) && !isKb(c)).sort(byStatusThenTitle);
  const manualCourses = courses.filter((c) => !isKb(c) && !isClassroom(c)).sort(byStatusThenTitle);

  const courseTags = status?.course_tags ?? 0;
  const googleLabel = status?.google.connected
    ? 'Google connected'
    : status?.google.configured
      ? 'Google not connected'
      : 'Google not configured';

  return (
    <div>
      <Header title="Courses" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total</div><div className="value">{courses.length}</div></div>
        <div className="stat-tile"><div className="label">Active</div><div className="value">{inProgress.length}</div></div>
        <div className="stat-tile"><div className="label">Completed</div><div className="value">{completed.length}</div></div>
      </div>

      <div className="sync-actions">
        <button className="btn" onClick={syncKb} disabled={syncing !== null}>
          <span className="emoji">🧠</span> {syncing === 'kb' ? 'Syncing…' : 'Sync from Second Brain'}
        </button>
        <button className="btn" onClick={syncClassroom} disabled={syncing !== null}>
          <span className="emoji">🏫</span> {syncing === 'classroom' ? 'Syncing…' : 'Sync Google Classroom'}
        </button>
      </div>

      {message && <div className="notice notice-info">{message}</div>}

      {status && (
        <div className="sync-status" data-testid="sync-status">
          <span title="Second Brain sources (folders)"><span className="emoji">📂</span> {status.sources} source{status.sources === 1 ? '' : 's'}</span>
          <span title="Second Brain documents"><span className="emoji">📄</span> {status.documents} document{status.documents === 1 ? '' : 's'}</span>
          <span title="Notes tagged course:&lt;name&gt;"><span className="emoji">🏷️</span> {courseTags} course tag{courseTags === 1 ? '' : 's'}</span>
          <span title="Subjects derived from top-level vault folders"><span className="emoji">📁</span> {status?.course_folders ?? 0} folder subject{status?.course_folders === 1 ? '' : 's'}</span>
          <span title="Last automatic/manual KB sync"><span className="emoji">🕒</span> last sync {formatTime(status.last_sync?.synced_at)}</span>
          <span className={status.google.connected ? 'sync-status-live' : ''} title="Google Classroom connection">
            <span className="emoji">🔗</span> {googleLabel}
          </span>
        </div>
      )}

      {/* Every subject fully visible — no horizontal sliding rows. When the
          vault is completely empty the big “No courses yet” notice below covers
          everything, so the per-group hints only show for partial states. */}
      <CourseCardsGrid
        courses={kbCourses}
        title="Second Brain"
        emoji="🧠"
        emptyHint={courses.length === 0 ? undefined :
          'No subjects derived from Second Brain yet. Tag a note with '
          + 'course:<name> (e.g. course:Operating Systems) or keep notes in a top-level vault folder '
          + '(e.g. “Operating Systems/”), then hit “Sync from Second Brain”.'}
      />
      <CourseCardsGrid
        courses={classroomCourses}
        title="Google Classroom"
        emoji="🏫"
        emptyHint={courses.length === 0 ? undefined :
          'No Classroom courses linked yet — connect Google Classroom and sync to import your enrolled courses.'}
      />
      <CourseCardsGrid
        courses={manualCourses}
        title="Manual"
        emoji="✏️"
        emptyHint={courses.length === 0 ? undefined :
          'No manually created courses. Use the admin/curriculum pages to add one.'}
      />

      {courses.length === 0 && (
        <div className="notice notice-info">
          <strong>No courses yet.</strong> Courses come from three places:
          <ul style={{ margin: '0.4rem 0 0', paddingLeft: '1.2rem' }}>
            <li>Tag a Second Brain note with <code>course:&lt;name&gt;</code> (e.g. <code>course:Operating Systems</code>) then hit “Sync from Second Brain” — one course per tag.</li>
            <li>Or simply keep notes in a top-level vault folder (e.g. <code>Operating Systems/</code>) — folders become subjects automatically, no tagging needed.</li>
            <li>Connect Google Classroom and sync your enrolled courses.</li>
            <li>Create a course manually on the admin/curriculum pages.</li>
          </ul>
        </div>
      )}

      <AcademicResourcesGrid />
    </div>
  );
};
