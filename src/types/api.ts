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

// The backend wraps every error in this envelope (keys are camelCased at the
// HTTP boundary): { error: { code, message, details: [{ field, message, type }] } }.
export interface ApiEnvelopeErrorItem {
  field?: string;
  message?: string;
  type?: string;
}

export interface ApiEnvelopeError {
  code?: string;
  message?: string;
  details?: ApiEnvelopeErrorItem[];
  requestId?: string | null;
}

export interface ApiErrorResponse {
  // Canonical backend envelope.
  error?: ApiEnvelopeError;
  // Legacy / FastAPI-default shapes, kept for resilience.
  message?: string;
  detail?: string | ApiErrorDetail[];
  status?: number;
  errors?: Record<string, string[]>;
}
