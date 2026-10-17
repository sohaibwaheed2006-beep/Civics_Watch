import { apiClient } from '@/lib/api-client';

export interface WorkerBonus {
  id: number;
  periodYear: number;
  periodMonth: number;
  workerId: number;
  workerName: string | null;
  resolvedCount: number;
  averageRating: number;
  averageHoursToResolve: number | null;
  onTimeRate: number;
  totalScore: number;
  createdAt: string;
  updatedAt: string;
}

export interface WorkerScore {
  workerId: number;
  workerName: string;
  resolvedCount: number;
  averageRating: number;
  averageHoursToResolve: number | null;
  onTimeRate: number;
  totalScore: number;
}

export const bonusService = {
  async listRecent(limit = 12) {
    const response = await apiClient.get<WorkerBonus[]>('/bonus', {
      params: { limit },
    });
    return response.data;
  },

  async leaderboard() {
    const response = await apiClient.get<WorkerScore[]>(
      '/bonus/current-leaderboard'
    );
    return response.data;
  },

  async awardPreviousMonth(overwrite = false) {
    const response = await apiClient.post<WorkerBonus | null>(
      '/bonus/award/previous-month',
      null,
      { params: { overwrite } }
    );
    return response.data;
  },

  async awardMonth(year: number, month: number, overwrite = false) {
    const response = await apiClient.post<WorkerBonus | null>(
      `/bonus/award/${year}/${month}`,
      null,
      { params: { overwrite } }
    );
    return response.data;
  },
};
