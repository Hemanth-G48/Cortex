// Google/Classroom/Gmail/Calendar sync types.
// Extracted from services/api.ts (F8 split).

// ----- Google sync types (99-phase plan, Group 14) -----
export interface GoogleStatus {
  connected: boolean;
  email: string | null;
  scopes: string[];
}

export interface GoogleConnectResponse {
  url: string | null;
  error?: string | null;
}

export interface ClassroomCourse {
  id: string;
  name: string;
  description: string | null;
}

export interface ClassroomAssignment {
  id: string;
  courseId: string;
  courseName: string;
  title: string;
  description: string;
  dueDate: string | null;
  status: string;
}

// ``source`` labels whether the payload is live Google data or the
// deterministic offline demo (used when Google is not connected).
export type ClassroomSource = 'live' | 'mock';

export interface ClassroomCoursesResponse {
  courses: ClassroomCourse[];
  source: ClassroomSource;
}

export interface ClassroomAssignmentsResponse {
  assignments: ClassroomAssignment[];
  source: ClassroomSource;
}

export interface GmailMessage {
  id: string;
  from: string;
  subject: string;
  date: string;
  snippet: string;
}

export interface GmailUnread {
  count: number;
}

export interface CalendarSyncEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location: string | null;
  link: string | null;
}
