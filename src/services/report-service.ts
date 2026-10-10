import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import {
  Report,
  CreateReportPayload,
  ReportFilterParams,
  UpdateReportStatusPayload,
  AssignReportPayload,
} from '@/types/report';
import { PaginatedResponse } from '@/types/api';
import { MockBackendAdapter } from '@/lib/mock-adapter';
import { User } from '@/types/auth';

export const reportService = {
  async getReports(params: ReportFilterParams = {}): Promise<PaginatedResponse<Report>> {
    try {
      const response = await apiClient.get<PaginatedResponse<Report>>('/reports', { params });
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getReportsList(params);
      }
      throw error;
    }
  },

  async getReportById(id: string): Promise<Report> {
    try {
      const response = await apiClient.get<Report>(`/reports/${id}`);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getReportById(id);
      }
      throw error;
    }
  },

  async createReport(payload: CreateReportPayload, user: User): Promise<Report> {
    try {
      const formData = new FormData();
      formData.append('title', payload.title);
      formData.append('description', payload.description);
      formData.append('category', payload.category);
      formData.append('latitude', payload.latitude.toString());
      formData.append('longitude', payload.longitude.toString());
      if (payload.address) {
        formData.append('address', payload.address);
      }
      if (payload.photos && payload.photos.length > 0) {
        payload.photos.forEach((file) => {
          formData.append('photos', file);
        });
      }

      const response = await apiClient.post<Report>('/reports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.createReport(payload, user);
      }
      throw error;
    }
  },

  async updateReportStatus(
    id: string,
    payload: UpdateReportStatusPayload,
    user: User
  ): Promise<Report> {
    try {
      const response = await apiClient.patch<Report>(`/reports/${id}/status`, payload);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.updateReportStatus(id, payload, user);
      }
      throw error;
    }
  },

  async assignReport(id: string, payload: AssignReportPayload, user: User): Promise<Report> {
    try {
      const response = await apiClient.post<Report>(`/reports/${id}/assign`, payload);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.assignReport(id, payload, user);
      }
      throw error;
    }
  },

  async toggleUpvote(
    id: string,
    user: User
  ): Promise<{ upvotesCount: number; hasUpvoted: boolean }> {
    try {
      const response = await apiClient.post<{ upvotesCount: number; hasUpvoted: boolean }>(
        `/reports/${id}/upvote`
      );
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.toggleUpvote(id, user);
      }
      throw error;
    }
  },

  async deleteReport(id: string, user: User): Promise<void> {
    try {
      await apiClient.delete(`/reports/${id}`);
    } catch (error) {
      if (isMockFallbackEnabled()) {
        await MockBackendAdapter.deleteReport(id, user);
        return;
      }
      throw error;
    }
  },
};
