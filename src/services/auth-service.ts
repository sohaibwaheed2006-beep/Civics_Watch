import { apiClient, authStorage, isMockFallbackEnabled } from '@/lib/api-client';
import { AuthResponse, LoginCredentials, RegisterData, User } from '@/types/auth';
import { MockBackendAdapter } from '@/lib/mock-adapter';

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
      authStorage.setToken(response.data.accessToken);
      authStorage.setUser(response.data.user);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        const mockRes = await MockBackendAdapter.login(credentials);
        authStorage.setToken(mockRes.accessToken);
        authStorage.setUser(mockRes.user);
        return mockRes;
      }
      throw error;
    }
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>('/auth/register', data);
      authStorage.setToken(response.data.accessToken);
      authStorage.setUser(response.data.user);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        const mockRes = await MockBackendAdapter.register(data);
        authStorage.setToken(mockRes.accessToken);
        authStorage.setUser(mockRes.user);
        return mockRes;
      }
      throw error;
    }
  },

  async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<User>('/auth/me');
      authStorage.setUser(response.data);
      return response.data;
    } catch (error) {
      const storedUser = authStorage.getUser<User>();
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getCurrentUser(storedUser?.id);
      }
      if (storedUser) return storedUser;
      throw error;
    }
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore backend error on logout
    } finally {
      authStorage.clear();
    }
  },

  async changePassword(data: { currentPassword: string; newPassword: string }): Promise<void> {
    try {
      await apiClient.post('/auth/change-password', data);
    } catch (error) {
      if (isMockFallbackEnabled()) {
        await new Promise((r) => setTimeout(r, 400));
        return;
      }
      throw error;
    }
  },
};
