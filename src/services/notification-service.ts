import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import { Notification } from '@/types/notification';
import { MockBackendAdapter } from '@/lib/mock-adapter';

// The backend returns notifications as a paginated envelope, which the API
// client normalises to { data: [...] }. Mock returns a raw array. Accept both
// and always hand callers a plain array so `.filter`/`.map` never explode.
function toArray<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[];
  const data = (payload as { data?: unknown })?.data;
  return Array.isArray(data) ? (data as T[]) : [];
}

// Backend NotificationRead exposes `notificationType` (after camelCasing),
// while the UI reads `type`. Reconcile the field names and coerce ids to the
// strings the components expect.
function normalizeNotification(raw: any): Notification {
  if (!raw || typeof raw !== 'object') return raw;
  return {
    ...raw,
    id: String(raw.id),
    userId: raw.userId != null ? String(raw.userId) : raw.userId,
    reportId: raw.reportId != null ? String(raw.reportId) : undefined,
    type: raw.type ?? raw.notificationType,
  } as Notification;
}

export const notificationService = {
  async getNotifications(userId: string | number): Promise<Notification[]> {
    try {
      // The backend scopes the list to the authenticated user from the bearer
      // token, so no userId query parameter is sent.
      const response = await apiClient.get('/notifications');
      return toArray<Notification>(response.data).map(normalizeNotification);
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getNotificationsList(String(userId));
      }
      throw error;
    }
  },

  async markAsRead(id: string): Promise<void> {
    try {
      await apiClient.patch(`/notifications/${id}/read`);
    } catch (error) {
      if (isMockFallbackEnabled()) {
        await MockBackendAdapter.markNotificationRead(id);
        return;
      }
      throw error;
    }
  },

  async markAllAsRead(userId: string): Promise<void> {
    try {
      // Backend route is POST /notifications/mark-all-read; the user is taken
      // from the token, so no body is sent.
      await apiClient.post('/notifications/mark-all-read');
    } catch (error) {
      if (isMockFallbackEnabled()) {
        await MockBackendAdapter.markAllNotificationsRead(userId);
        return;
      }
      throw error;
    }
  },
};
