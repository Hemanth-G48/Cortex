import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import type {
  CalendarSyncEvent,
  ClassroomAssignment,
  ClassroomCourse,
  GmailMessage,
  GoogleStatus,
} from '../../services/api';

type SyncKind = 'classroom-courses' | 'classroom-assignments' | 'gmail' | 'calendar';

export default function GoogleSyncCard() {
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [courses, setCourses] = useState<ClassroomCourse[] | null>(null);
  const [assignments, setAssignments] = useState<ClassroomAssignment[] | null>(null);
  const [messages, setMessages] = useState<GmailMessage[] | null>(null);
  const [events, setEvents] = useState<CalendarSyncEvent[] | null>(null);
  const [unread, setUnread] = useState<number | null>(null);
  const [syncing, setSyncing] = useState<SyncKind | null>(null);

  const loadStatus = useCallback(() => {
    endpoints.google
      .status()
      .then((s) => {
        setStatus(s);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(loadStatus, [loadStatus]);

  const connect = async () => {
    setError(null);
    try {
      const res = await endpoints.google.connect();
      if (res.url) window.open(res.url, '_blank');
      else setError(res.error ?? 'Google OAuth not configured');
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const disconnect = async () => {
    setError(null);
    try {
      await endpoints.google.disconnect();
      setStatus({ connected: false, email: null, scopes: [] });
      setCourses(null);
      setAssignments(null);
      setMessages(null);
      setEvents(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const sync = async (kind: SyncKind) => {
    setSyncing(kind);
    setError(null);
    try {
      switch (kind) {
        case 'classroom-courses':
          setCourses(await endpoints.classroom.courses());
          break;
        case 'classroom-assignments':
          setAssignments(await endpoints.classroom.assignments());
          break;
        case 'gmail':
          setMessages(await endpoints.gmail.messages(5));
          setUnread((await endpoints.gmail.unread()).count);
          break;
        case 'calendar':
          setEvents(await endpoints.calendarSync.events());
          break;
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>
          <span className="emoji">🔗</span> Google Sync
        </h2>
        <span className={`badge ${status?.connected ? 'badge-success' : 'badge-muted'}`}>
          {status?.connected ? `Connected${status.email ? ` · ${status.email}` : ''}` : 'Not connected'}
        </span>
      </div>

      <p className="panel-sub">
        Import your Google Classroom courses & assignments, Gmail study mail, and Calendar events —
        merged idempotently into your local data (read-only scopes).
      </p>

      {error && <div className="notice notice-error">{error}</div>}

      <div className="sync-actions">
        {!status?.connected ? (
          <button className="btn btn-primary" onClick={connect} disabled={loading}>
            <span className="emoji">🔑</span> Connect Google
          </button>
        ) : (
          <button className="btn btn-danger-ghost" onClick={disconnect}>
            Disconnect
          </button>
        )}

        <button
          className="btn"
          onClick={() => sync('classroom-courses')}
          disabled={syncing !== null}
        >
          <span className="emoji">🏫</span> {syncing === 'classroom-courses' ? 'Syncing…' : 'Sync Classroom Courses'}
        </button>
        <button
          className="btn"
          onClick={() => sync('classroom-assignments')}
          disabled={syncing !== null}
        >
          <span className="emoji">📝</span> {syncing === 'classroom-assignments' ? 'Syncing…' : 'Sync Assignments'}
        </button>
        <button className="btn" onClick={() => sync('gmail')} disabled={syncing !== null}>
          <span className="emoji">📬</span> {syncing === 'gmail' ? 'Syncing…' : 'Sync Gmail'}
        </button>
        <button className="btn" onClick={() => sync('calendar')} disabled={syncing !== null}>
          <span className="emoji">📅</span> {syncing === 'calendar' ? 'Syncing…' : 'Sync Calendar'}
        </button>
      </div>

      {unread !== null && (
        <div className="stat-row">
          <span className="emoji">🔔</span> {unread} unread study-related messages
        </div>
      )}

      {courses && courses.length > 0 && (
        <div className="sync-results">
          <h4>Classroom courses</h4>
          <ul>
            {courses.map((c) => (
              <li key={c.id}>
                <strong>{c.name}</strong>
                {c.description ? <span className="muted"> — {c.description}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      )}

      {assignments && assignments.length > 0 && (
        <div className="sync-results">
          <h4>Assignments imported</h4>
          <ul>
            {assignments.map((a) => (
              <li key={a.id}>
                <strong>{a.title}</strong>
                <span className="muted"> · {a.courseName}</span>
                {a.dueDate ? <span className="muted"> · due {a.dueDate}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      )}

      {messages && messages.length > 0 && (
        <div className="sync-results">
          <h4>Recent mail</h4>
          <ul>
            {messages.map((m) => (
              <li key={m.id}>
                <strong>{m.subject}</strong>
                <span className="muted"> · {m.from}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {events && events.length > 0 && (
        <div className="sync-results">
          <h4>Calendar events</h4>
          <ul>
            {events.map((e) => (
              <li key={e.id}>
                <strong>{e.title}</strong>
                <span className="muted"> · {e.start}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(courses?.length === 0 || assignments?.length === 0 || messages?.length === 0 || events?.length === 0) && (
        <div className="notice notice-info">Nothing found — try connecting Google first.</div>
      )}
    </div>
  );
}
