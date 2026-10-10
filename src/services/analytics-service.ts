import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import { AnalyticsSummary } from '@/types/analytics';
import { MockBackendAdapter } from '@/lib/mock-adapter';

export const analyticsService = {
  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    try {
      const response = await apiClient.get<AnalyticsSummary>('/analytics/overview');
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getAnalytics();
      }
      throw error;
    }
  },
};
