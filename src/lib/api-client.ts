import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import { API_BASE_URL } from './constants';

const TOKEN_STORAGE_KEY = 'nir_auth_token';
const USER_STORAGE_KEY = 'nir_auth_user';

// ---------------------------------------------------------------------------
// Case conversion between the backend (snake_case) and the frontend
// (camelCase). The backend returns `full_name`, `access_token`, `created_at`
// etc.; our components work with `fullName`, `accessToken`, `createdAt`.
// Rather than touch every call site, we normalise at the HTTP boundary.
// ---------------------------------------------------------------------------
function toCamelCaseKey(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
}

function toSnakeCaseKey(key: string): string {
  return key.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return (
    value !== null &&
    typeof value === 'object' &&
    (value.constructor === Object || Object.getPrototypeOf(value) === null)
  );
}

function convertKeysDeep(
  input: unknown,
  convert: (key: string) => string
): unknown {
  if (Array.isArray(input)) {
    return input.map((item) => convertKeysDeep(item, convert));
  }
  if (isPlainObject(input)) {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(input)) {
      out[convert(key)] = convertKeysDeep(value, convert);
    }
    return out;
  }
  return input;
}

export const toCamelCase = (v: unknown): unknown => convertKeysDeep(v, toCamelCaseKey);
export const toSnakeCase = (v: unknown): unknown => convertKeysDeep(v, toSnakeCaseKey);

// ---------------------------------------------------------------------------
// Pagination envelope normaliser
// Backend returns { items: [...], meta: { page, pageSize, totalItems, ...} }.
// Frontend expects   { data: [...], total, page, limit, totalPages }.
// ---------------------------------------------------------------------------
function normalizePage(payload: unknown): unknown {
  if (!isPlainObject(payload)) return payload;
  if (!Array.isArray((payload as Record<string, unknown>).items)) return payload;
  const items = (payload as Record<string, unknown>).items as unknown[];
  const meta = ((payload as Record<string, unknown>).meta ?? {}) as Record<string, unknown>;
  const page = Number(meta.page ?? 1);
  const pageSize = Number(meta.pageSize ?? items.length ?? 0);
  const totalItems = Number(meta.totalItems ?? items.length ?? 0);
  const totalPages = Number(meta.totalPages ?? (pageSize > 0 ? Math.ceil(totalItems / pageSize) : 0));
  return {
    data: items,
    total: totalItems,
    page,
    limit: pageSize,
    totalPages,
  };
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Attach bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Convert JSON request bodies to snake_case so the FastAPI schemas accept
    // them. FormData / Blob bodies are left untouched (multipart uploads).
    const skipTransform = (config as AxiosRequestConfig & { skipCaseTransform?: boolean })
      .skipCaseTransform;
    if (!skipTransform && config.data && !(config.data instanceof FormData) && !(config.data instanceof Blob)) {
      config.data = toSnakeCase(config.data);
    }

    // For multipart uploads the browser MUST set the Content-Type itself so it
    // includes the `boundary=...` parameter. The instance default
    // ('application/json') and any hand-set 'multipart/form-data' header lack
    // the boundary and make the server reject the body with
    // "Missing boundary in multipart". Deleting the header here lets axios set
    // the correct one with the boundary.
    if (config.data instanceof FormData && config.headers) {
      const headers = config.headers as unknown as {
        delete?: (name: string) => void;
        [key: string]: unknown;
      };
      if (typeof headers.delete === 'function') {
        headers.delete('Content-Type');
      } else {
        delete headers['Content-Type'];
      }
    }

    // Query params also go through the snake_case converter.
    if (!skipTransform && config.params) {
      config.params = toSnakeCase(config.params);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Normalise responses: snake_case -> camelCase, and {items,meta} -> {data,...}.
apiClient.interceptors.response.use(
  (response) => {
    if (response.data && typeof response.data === 'object') {
      const camel = toCamelCase(response.data);
      response.data = normalizePage(camel);
    }
    return response;
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname;
      if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        localStorage.removeItem(USER_STORAGE_KEY);
      }
    }
    // Still camelCase-normalise error payloads so parsers can read them.
    if (error.response?.data && typeof error.response.data === 'object') {
      error.response.data = toCamelCase(error.response.data) as typeof error.response.data;
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
