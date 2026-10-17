import { apiClient, authStorage } from '@/lib/api-client';
import { AuthResponse, LoginCredentials, RegisterData, User } from '@/types/auth';
import { AxiosError } from 'axios';

// The backend returns a UserRead object from /auth/register (no token) and an
// AuthResponse (token + user) from /auth/login. We expose a single
// AuthResponse-shaped result to the UI by composing the two calls when needed.
interface RawAuthResponse {
  accessToken: string;
  tokenType: string;
  expiresIn?: number;
  user: User;
}

// Authentication is ALWAYS validated by the real backend. There is deliberately
// no mock fallback in this service: wrong credentials must be rejected, and an
// unreachable backend must surface a real error rather than silently granting
// access. (Other, non-security services may still fall back to mock data.)
export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<RawAuthResponse>('/auth/login', credentials);
    const data = response.data;
    authStorage.setToken(data.accessToken);
    authStorage.setUser(data.user);
    return {
      accessToken: data.accessToken,
      tokenType: data.tokenType,
      user: data.user,
    };
  },

  async register(data: RegisterData): Promise<User> {
    // Backend register returns the created user (no token). We deliberately do
    // NOT log the user in here: after registering, the person is sent to the
    // sign-in page to authenticate explicitly. A failure here (e.g. email
    // already registered) propagates to the form. No token/user is stored.
    const response = await apiClient.post<User>('/auth/register', {
      fullName: data.fullName,
      email: data.email,
      password: data.password,
      phone: data.phone,
    });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    // Called on app bootstrap to restore a session from a stored token.
    try {
      const response = await apiClient.get<User>('/auth/me');
      authStorage.setUser(response.data);
      return response.data;
    } catch (error) {
      const status = (error as AxiosError)?.response?.status;
      // A 401 means the stored token is invalid or expired: the session is
      // over, so clear it and surface the error (the auth context logs out).
      if (status === 401) {
        authStorage.clear();
        throw error;
      }
      // Transient/network error: keep the current session alive using the
      // cached user rather than logging the person out over a blip.
      const storedUser = authStorage.getUser<User>();
      if (storedUser) return storedUser;
      throw error;
    }
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore backend error on logout.
    } finally {
      authStorage.clear();
    }
  },

  async changePassword(data: { currentPassword: string; newPassword: string }): Promise<void> {
    await apiClient.post('/auth/change-password', data);
  },

  // Request a password-reset link. The backend returns the same generic
  // acknowledgement whether or not the email is registered (no enumeration),
  // so callers should always show the same success state.
  async forgotPassword(email: string): Promise<string> {
    const response = await apiClient.post<{ message: string }>('/auth/forgot-password', {
      email,
    });
    return response.data.message;
  },

  // Complete a reset using the token from the emailed link. `newPassword` is
  // converted to `new_password` by the api-client's snake_case transform.
  async resetPassword(token: string, newPassword: string): Promise<string> {
    const response = await apiClient.post<{ message: string }>('/auth/reset-password', {
      token,
      newPassword,
    });
    return response.data.message;
  },

};
