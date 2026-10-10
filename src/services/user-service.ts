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
    try {
      const response = await apiClient.get<PaginatedResponse<UserListItem>>('/users', { params });
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
