import { apiClient } from '@/lib/api-client';

export interface Review {
  id: number;
  reportId: number;
  workerId: number;
  citizenId: number;
  rating: number;
  comment: string | null;
  createdAt: string;
  updatedAt: string;
}

export const reviewService = {
  async submit(reportId: string | number, rating: number, comment?: string) {
    const response = await apiClient.post<Review>(
      `/reports/${reportId}/review`,
      { rating, comment: comment || null }
    );
    return response.data;
  },

  async getMine(reportId: string | number): Promise<Review | null> {
    const response = await apiClient.get<Review | null>(
      `/reports/${reportId}/review`
    );
    return response.data || null;
  },
};
