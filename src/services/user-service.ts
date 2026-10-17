import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import {
  UserListItem,
  UserFilterParams,
  CreateWorkerPayload,
  UpdateUserPayload,
} from '@/types/user';
import { User } from '@/types/auth';
import { PaginatedResponse } from '@/types/api';
import { MockBackendAdapter } from '@/lib/mock-adapter';

export const userService = {
  async getUsers(params: UserFilterParams = {}): Promise<PaginatedResponse<UserListItem>> {
    // The backend validates every query parameter strictly. Sending an empty
    // `search` (min_length=1), a `role`/`departmentId` of 'all', or the key
    // `limit` (the endpoint expects `page_size`) makes it answer 422 — which
    // silently drops us onto mock data. That is exactly why citizens who
    // registered against the real backend never showed up in the directory.
    // Translate to the backend's contract and only send a filter that is set.
    const query: Record<string, unknown> = {
      page: params.page ?? 1,
      page_size: params.limit ?? 10,
    };
    if (params.search && params.search.trim()) query.search = params.search.trim();
    if (params.role && params.role !== 'all') query.role = params.role;
    if (params.departmentId && params.departmentId !== 'all') {
      query.department_id = params.departmentId;
    }
    if (params.isActive !== undefined) query.is_active = params.isActive;

    try {
      const response = await apiClient.get<PaginatedResponse<UserListItem>>('/users', {
        params: query,
      });
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getUsersList(params);
      }
      throw error;
    }
  },

  async createWorker(payload: CreateWorkerPayload): Promise<User> {
    try {
      const response = await apiClient.post<User>('/users/workers', payload);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.createWorker(payload);
      }
      throw error;
    }
  },

  async updateUser(id: string, payload: UpdateUserPayload): Promise<User> {
    try {
      const response = await apiClient.patch<User>(`/users/${id}`, payload);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.updateUser(id, payload);
      }
      throw error;
    }
  },
};
