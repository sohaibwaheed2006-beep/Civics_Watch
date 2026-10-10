import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import { Assignment, AssignmentFilterParams } from '@/types/assignment';
import { PaginatedResponse } from '@/types/api';
import { MockBackendAdapter } from '@/lib/mock-adapter';

export const assignmentService = {
  async getWorkerAssignments(
    workerId: string,
    params: AssignmentFilterParams = {}
  ): Promise<PaginatedResponse<Assignment>> {
    try {
      const response = await apiClient.get<PaginatedResponse<Assignment>>(
        `/workers/${workerId}/assignments`,
        { params }
      );
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getWorkerAssignments(workerId, params);
      }
      throw error;
    }
  },
};
