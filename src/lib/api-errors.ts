import axios, { AxiosError } from 'axios';
import { ApiErrorResponse, ApiErrorDetail } from '@/types/api';

export interface ParsedApiError {
  message: string;
  // Stable backend error code from the envelope (e.g. 'unauthorized',
  // 'not_found', 'conflict'), when present. Branch on this rather than the message.
  code?: string;
  fieldErrors?: Record<string, string>;
  status?: number;
  isNetworkError: boolean;
  isAuthError: boolean;
}

export function parseApiError(error: unknown): ParsedApiError {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<ApiErrorResponse>;
    const status = axiosErr.response?.status;
    const data = axiosErr.response?.data;

    if (!axiosErr.response) {
      return {
        message: 'Cannot reach the server. Please check your internet connection or backend status.',
        status: undefined,
        isNetworkError: true,
        isAuthError: false,
      };
    }

    const fieldErrors: Record<string, string> = {};

    // Canonical backend envelope: { error: { code, message, details: [...] } }.
    // This is the shape THIS API actually returns, so it is checked first.
    // Without this branch every error fell through to the generic per-status
    // message below (e.g. a failed login showed "session expired" instead of
    // "Incorrect email or password.").
    if (data?.error && typeof data.error === 'object') {
      const envelope = data.error;
      (envelope.details ?? []).forEach((item) => {
        // `field` looks like "body.email" / "query.page" / "__request__".
        // Use the last dotted segment as the form field name.
        const rawField = item.field ?? '';
        const fieldName = rawField.split('.').pop() ?? '';
        if (fieldName && fieldName !== 'body' && fieldName !== '__request__' && item.message) {
          fieldErrors[fieldName] = item.message;
        }
      });

      const message =
        envelope.message ||
        'Something went wrong. Please check the entered information and try again.';

      return {
        message,
        code: envelope.code,
        fieldErrors: Object.keys(fieldErrors).length > 0 ? fieldErrors : undefined,
        status,
        isNetworkError: false,
        isAuthError: status === 401 || status === 403,
      };
    }

    // FastAPI 422 validation errors format: { detail: [{ loc: [...], msg: "..." }] }
    if (data?.detail && Array.isArray(data.detail)) {
      const messages: string[] = [];
      data.detail.forEach((item: ApiErrorDetail) => {
        const fieldName = item.loc ? String(item.loc[item.loc.length - 1]) : '';
        if (fieldName && fieldName !== 'body') {
          fieldErrors[fieldName] = item.msg;
          messages.push(`${fieldName}: ${item.msg}`);
        } else {
          messages.push(item.msg);
        }
      });

      return {
        message: messages.join('. ') || 'Validation error. Please verify the entered fields.',
        fieldErrors: Object.keys(fieldErrors).length > 0 ? fieldErrors : undefined,
        status,
        isNetworkError: false,
        isAuthError: false,
      };
    }

    // Single detail string
    if (typeof data?.detail === 'string') {
      return {
        message: data.detail,
        status,
        isNetworkError: false,
        isAuthError: status === 401 || status === 403,
      };
    }

    if (data?.message) {
      return {
        message: data.message,
        status,
        isNetworkError: false,
        isAuthError: status === 401 || status === 403,
      };
    }

    // Default messages by status code
    switch (status) {
      case 400:
        return {
          message: 'Bad Request. The request parameters were invalid.',
          status,
          isNetworkError: false,
          isAuthError: false,
        };
      case 401:
        return {
          message: 'Your session has expired or you are not logged in. Please sign in again.',
          status,
          isNetworkError: false,
          isAuthError: true,
        };
      case 403:
        return {
          message: 'Access Denied. You do not have permission to perform this action.',
          status,
          isNetworkError: false,
          isAuthError: true,
        };
      case 404:
        return {
          message: 'The requested resource could not be found.',
          status,
          isNetworkError: false,
          isAuthError: false,
        };
      case 409:
        return {
          message: 'Conflict detected. A conflicting resource or duplicate status exists.',
          status,
          isNetworkError: false,
          isAuthError: false,
        };
      case 429:
        return {
          message: 'Rate limit exceeded. Please wait a moment and try again.',
          status,
          isNetworkError: false,
          isAuthError: false,
        };
      case 500:
      case 502:
      case 503:
        return {
          message: 'A backend server error occurred. Please try again shortly.',
          status,
          isNetworkError: false,
          isAuthError: false,
        };
      default:
        return {
          message: axiosErr.message || 'An unexpected error occurred.',
          status,
          isNetworkError: false,
          isAuthError: false,
        };
    }
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      isNetworkError: false,
      isAuthError: false,
    };
  }

  return {
    message: 'An unknown error occurred.',
    isNetworkError: false,
    isAuthError: false,
  };
}
