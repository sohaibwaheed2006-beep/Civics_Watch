import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import {
  Department,
  CreateDepartmentPayload,
  UpdateDepartmentPayload,
} from '@/types/department';
import { MockBackendAdapter } from '@/lib/mock-adapter';

// /departments returns a paginated envelope normalised to { data: [...] };
// mock returns a raw array. Accept both and always return a plain array.
function toArray<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[];
  const data = (payload as { data?: unknown })?.data;
  return Array.isArray(data) ? (data as T[]) : [];
}

export const departmentService = {
  async getDepartments(): Promise<Department[]> {
    try {
      const response = await apiClient.get('/departments', {
        params: { page: 1, page_size: 100 },
      });
      return toArray<Department>(response.data);
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
