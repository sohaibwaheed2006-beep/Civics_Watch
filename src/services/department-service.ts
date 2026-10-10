import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import {
  Department,
  CreateDepartmentPayload,
  UpdateDepartmentPayload,
} from '@/types/department';
import { MockBackendAdapter } from '@/lib/mock-adapter';

export const departmentService = {
  async getDepartments(): Promise<Department[]> {
    try {
      const response = await apiClient.get<Department[]>('/departments');
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getDepartmentsList();
      }
      throw error;
    }
  },

  async createDepartment(payload: CreateDepartmentPayload): Promise<Department> {
    try {
      const response = await apiClient.post<Department>('/departments', payload);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.createDepartment(payload);
      }
      throw error;
    }
  },

  async updateDepartment(id: string, payload: UpdateDepartmentPayload): Promise<Department> {
    try {
      const response = await apiClient.patch<Department>(`/departments/${id}`, payload);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.updateDepartment(id, payload);
      }
      throw error;
    }
  },
};
