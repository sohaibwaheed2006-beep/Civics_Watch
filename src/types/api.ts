export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg: string;
  type?: string;
}

export interface ApiErrorResponse {
  message?: string;
  detail?: string | ApiErrorDetail[];
  status?: number;
  errors?: Record<string, string[]>;
}
