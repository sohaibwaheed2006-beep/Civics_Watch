import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import { Notification } from '@/types/notification';
import { MockBackendAdapter } from '@/lib/mock-adapter';

export const notificationService = {
  async getNotifications(userId: string): Promise<Notification[]> {
    try {
      const response = await apiClient.get<Notification[]>('/notifications', {
        params: { userId },
      });
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getNotificationsList(userId);
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
      await apiClient.post('/notifications/read-all', { userId });
    } catch (error) {
      if (isMockFallbackEnabled()) {
        await MockBackendAdapter.markAllNotificationsRead(userId);
        return;
      }
      throw error;
    }
  },
};
