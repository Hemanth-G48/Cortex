// Endpoint client for this domain — extracted from services/api.ts (F8 split).

import { api } from '../core'
import type { AppNotification, BrainDump, DailyCategory, DailyScheduleItem, DailyScheduleStats, EnergyLevel } from '../types/task'

export const brainDumpApi = {
  get: () => api.get<{ content: string | null; linked_document_id?: number | null }>('/braindumps'),
  save: (content: string) => api.put<BrainDump>('/braindumps', { content }),
};


export const dailyScheduleApi = {
  list: (date: string) => api.get<DailyScheduleItem[]>(`/dailyschedule?date=${date}`),
  create: (d: {
    date: string;
    time_range: string;
    activity: string;
    category?: DailyCategory;
    location?: string | null;
    energy?: EnergyLevel;
    notes?: string | null;
  }) => api.post<DailyScheduleItem>('/dailyschedule', d),
  update: (id: number, d: Partial<Omit<DailyScheduleItem, 'id' | 'created_at'>>) =>
    api.put<DailyScheduleItem>(`/dailyschedule/${id}`, d),
  remove: (id: number) => api.del<{ ok: boolean }>(`/dailyschedule/${id}`),
  toggle: (id: number) => api.post<DailyScheduleItem>(`/dailyschedule/${id}/toggle`),
  stats: (date: string) => api.get<DailyScheduleStats>(`/dailyschedule/stats?date=${date}`),
};


export const notificationApi = {
  list: () => api.get<AppNotification[]>('/notifications'),
  unreadCount: () => api.get<{ unread: number }>('/notifications/unread-count'),
  markRead: (id: number) => api.post<AppNotification>(`/notifications/${id}/read`),
  markAllRead: () => api.post<{ ok: boolean }>('/notifications/mark-all-read'),
  remove: (id: number) => api.del<{ ok: boolean }>(`/notifications/${id}`),
  clearAll: () => api.del<{ ok: boolean; deleted: number }>('/notifications'),
};

