// API client — split by domain (F8).
//
// This file is a re-export barrel. Domain types live in ``api/types/``
// and endpoint functions live in ``api/endpoints/``.
//
// Legacy imports (``import { Course, User } from '../services/api'``)
// continue to work unchanged.

// Core request helper + base api object
export { api, downloadAsFile } from './api/core'

// Types
export * from './api/types'

// ----- Profile / mood / related-docs endpoints -----
export { profileApi, moodApi, kbRelatedApi } from './api/endpoints/profile'

// ----- Upload endpoints -----
export { uploadApi } from './api/endpoints/upload'

// ----- Second Brain endpoints (defect fixes #12, #77, #79, #2) -----
export { kbSearchApi, kbGraphApi, quizzesHistoryApi, kbCaptureXpApi } from './api/endpoints/kb'

// ----- Core ``endpoints`` object (curriculum, materials, summaries, quizzes,
// enrollment, admin, analytics, google, classroom, gmail, calendarSync,
// studyPlans, flashcards, leaderboard, grades, ai, courses, assignments,
// exams, notes, goals, tasks, habits, fitness, vault, kb, subjects, ...) -----
export { endpoints } from './api/endpoints/index'

// ----- Books + Book Gap Analyzer -----
export { bookApi, bookGapApi } from './api/endpoints/book'

// ----- Brain dumps / daily schedule / notifications -----
export { brainDumpApi, dailyScheduleApi, notificationApi } from './api/endpoints/task'

// ----- SyllabusAI API clients (aliases over `endpoints` for named imports) -----
import { endpoints as _endpoints } from './api/endpoints/index'
export const curriculumApi = _endpoints.curriculum
export const materialApi = _endpoints.materials
export const summaryApi = _endpoints.summaries
export const quizApi = _endpoints.quizzes
export const adminApi = _endpoints.admin
export const enrollmentApi = _endpoints.enrollment
