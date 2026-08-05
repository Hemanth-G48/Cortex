import { useState, useEffect, useCallback } from 'react';
import { notificationApi, type AppNotification } from '../services/api';

interface UseNotificationsReturn {
  notifications: AppNotification[];
  unread: number;
  refresh: () => Promise<void>;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
  remove: (id: number) => Promise<void>;
  clearAll: () => Promise<void>;
}

export const useNotifications = (): UseNotificationsReturn => {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const [list, count] = await Promise.all([notificationApi.list(), notificationApi.unreadCount()]);
      setNotifications(list);
      setUnread(count.unread);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(id);
  }, [refresh]);

  const markRead = useCallback(async (id: number) => {
    try {
      await notificationApi.markRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnread((prev) => Math.max(0, prev - 1));
    } catch {
      /* silent */
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await notificationApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
    } catch {
      /* silent */
    }
  }, []);

  const remove = useCallback(async (id: number) => {
    try {
      await notificationApi.remove(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch {
      /* silent */
    }
  }, []);

  const clearAll = useCallback(async () => {
    try {
      await notificationApi.clearAll();
      setNotifications([]);
      setUnread(0);
    } catch {
      /* silent */
    }
  }, []);

  return { notifications, unread, refresh, markRead, markAllRead, remove, clearAll };
};
