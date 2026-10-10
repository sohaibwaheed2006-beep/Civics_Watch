import axios, { AxiosError } from 'axios';
import { API_BASE_URL } from './constants';

const TOKEN_STORAGE_KEY = 'nir_auth_token';
const USER_STORAGE_KEY = 'nir_auth_user';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Request interceptor to attach bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear token if expired or unauthorized
      const currentPath = window.location.pathname;
      if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
        // Prevent infinite loops
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        localStorage.removeItem(USER_STORAGE_KEY);
      }
    }
    return Promise.reject(error);
  }
);

export const authStorage = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  },
  setToken(token: string): void {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  },
  getUser<T>(): T | null {
    const userStr = localStorage.getItem(USER_STORAGE_KEY);
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  },
  setUser<T>(user: T): void {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  },
  clear(): void {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
  },
};

export const isMockFallbackEnabled = (): boolean => {
  return import.meta.env.VITE_ENABLE_MOCK_FALLBACK === 'true' || !import.meta.env.VITE_API_BASE_URL;
};
