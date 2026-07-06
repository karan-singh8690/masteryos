/**
 * Typed API client with authentication, refresh token, and error handling.
 *
 * Features:
 * - Axios instance with base URL + JSON content type
 * - Request interceptor: adds Authorization header + correlation ID + idempotency key
 * - Response interceptor: normalizes errors
 * - 401 interceptor: automatically refreshes the access token + retries
 * - Pagination helpers
 * - File upload support
 */

import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'

import {
  API_BASE_URL,
  REFRESH_TOKEN_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} from '@/lib/constants'
import type { ApiErrorResponse, PaginatedResponse, PaginationParams } from '@/types/common'

// ============================================================
// Token storage (abstracted for testability + SSR safety)
// ============================================================

const tokenStorage = {
  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  },
  setAccessToken(token: string): void {
    if (typeof window === 'undefined') return
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  },
  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
  },
  setRefreshToken(token: string): void {
    if (typeof window === 'undefined') return
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token)
  },
  clear(): void {
    if (typeof window === 'undefined') return
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
  },
}

export { tokenStorage }

// ============================================================
// Error normalization
// ============================================================

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly code: string,
    public readonly fieldErrors?: Record<string, string[]>,
    public readonly correlationId?: string,
    // Preserve the full detail object from the backend so callers can
    // access extra fields like existing_session_id, etc.
    public readonly detail?: Record<string, unknown>,
  ) {
    super(message)
    this.name = 'ApiError'
  }

  static fromAxiosError(error: AxiosError<ApiErrorResponse>): ApiError {
    // Network error (no response)
    if (!error.response) {
      return new ApiError(
        'Network error — please check your connection and try again.',
        0,
        'NETWORK_ERROR',
      )
    }

    const { status, data } = error.response
    const detail = data?.detail

    // Normalized error from backend
    if (detail && typeof detail === 'object' && 'code' in detail) {
      return new ApiError(
        detail.message || 'An error occurred.',
        status,
        detail.code,
        detail.fields,
        error.config?.headers?.['X-Correlation-ID'] as string | undefined,
        // Pass the full detail object (includes existing_session_id, etc.)
        detail as Record<string, unknown>,
      )
    }

    // Fallback
    return new ApiError(
      typeof detail === 'string' ? detail : 'An unexpected error occurred.',
      status,
      'UNKNOWN_ERROR',
    )
  }
}

// ============================================================
// Correlation ID + Idempotency Key generators
// ============================================================

function generateCorrelationId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

// ============================================================
// Axios instance
// ============================================================

const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================================
// Request interceptor: add auth + correlation ID
// ============================================================

axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add access token
    const token = tokenStorage.getAccessToken()
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add correlation ID (for distributed tracing)
    if (!config.headers['X-Correlation-ID']) {
      config.headers['X-Correlation-ID'] = generateCorrelationId()
    }

    // Add idempotency key for POST/PUT/PATCH (for safe retries)
    if (
      ['post', 'put', 'patch'].includes(config.method || '') &&
      !config.headers['Idempotency-Key']
    ) {
      config.headers['Idempotency-Key'] = generateIdempotencyKey()
    }

    return config
  },
  (error) => Promise.reject(error),
)

// ============================================================
// Refresh token handling
// ============================================================

let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null
let onTokenRefreshed: ((token: string) => void) | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  const refreshToken = tokenStorage.getRefreshToken()
  if (!refreshToken) {
    return null
  }

  isRefreshing = true
  refreshPromise = (async () => {
    try {
      // Use a separate axios instance to avoid interceptor recursion
      const response = await axios.post(
        `${API_BASE_URL}/auth/refresh`,
        { refresh_token: refreshToken },
        { headers: { 'Content-Type': 'application/json' } },
      )
      const newToken = response.data.access_token as string
      const newRefresh = response.data.refresh_token as string | null

      tokenStorage.setAccessToken(newToken)
      if (newRefresh) {
        tokenStorage.setRefreshToken(newRefresh)
      }

      // Notify waiting requests
      onTokenRefreshed?.(newToken)
      onTokenRefreshed = null

      return newToken
    } catch {
      // Refresh failed — clear tokens + redirect to login
      tokenStorage.clear()
      if (typeof window !== 'undefined') {
        window.location.href = '/session-expired'
      }
      return null
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()

  return refreshPromise
}

// ============================================================
// Response interceptor: handle 401 + normalize errors
// ============================================================

axiosInstance.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<ApiErrorResponse>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    // 401 → try to refresh + retry
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !originalRequest.url?.includes('/auth/login')
    ) {
      originalRequest._retry = true

      const newToken = await refreshAccessToken()
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return axiosInstance(originalRequest)
      }
    }

    return Promise.reject(ApiError.fromAxiosError(error))
  },
)

// ============================================================
// API client
// ============================================================

export const apiClient = {
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosInstance.get<T>(url, config)
    return response.data
  },

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosInstance.post<T>(url, data, config)
    return response.data
  },

  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosInstance.patch<T>(url, data, config)
    return response.data
  },

  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosInstance.put<T>(url, data, config)
    return response.data
  },

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosInstance.delete<T>(url, config)
    return response.data
  },

  /**
   * Upload a file (multipart/form-data).
   */
  async upload<T>(
    url: string,
    file: File | Blob,
    fieldName: string = 'file',
    additionalData?: Record<string, string>,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const formData = new FormData()
    formData.append(fieldName, file)
    if (additionalData) {
      for (const [key, value] of Object.entries(additionalData)) {
        formData.append(key, value)
      }
    }
    const response = await axiosInstance.post<T>(url, formData, {
      ...config,
      headers: {
        ...config?.headers,
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

// ============================================================
// Pagination helpers
// ============================================================

export function paginationParams(params?: PaginationParams): Record<string, string> {
  const result: Record<string, string> = {}
  if (params?.page) result.page = String(params.page)
  if (params?.pageSize) result.page_size = String(params.pageSize)
  if (params?.sortBy) result.sort_by = params.sortBy
  if (params?.sortOrder) result.sort_order = params.sortOrder
  return result
}

export function toPaginatedResponse<T>(
  items: T[],
  total: number,
  params: PaginationParams,
): PaginatedResponse<T> {
  const page = params.page ?? 1
  const pageSize = params.pageSize ?? 20
  return {
    items,
    total,
    page,
    pageSize,
    hasNext: page * pageSize < total,
    hasPrev: page > 1,
  }
}

// ============================================================
// Auth API
// ============================================================

export const authApi = {
  register: (data: import('@/types/auth').RegisterRequest) =>
    apiClient.post<import('@/types/auth').AuthResponse>('/auth/register', data),

  login: (data: import('@/types/auth').LoginRequest) =>
    apiClient.post<import('@/types/auth').AuthResponse>('/auth/login', data),

  refresh: (refreshToken: string) =>
    apiClient.post<import('@/types/auth').AuthResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    }),

  logout: (refreshToken?: string) =>
    apiClient.post<{ message: string }>('/auth/logout', refreshToken ? { refresh_token: refreshToken } : undefined),

  logoutAll: () => apiClient.post<{ message: string }>('/auth/logout-all'),

  verifyEmail: (token: string) =>
    apiClient.post<import('@/types/auth').User>('/auth/verify-email', { token }),

  resendVerification: (email: string) =>
    apiClient.post<{ message: string }>('/auth/resend-verification', { email }),

  forgotPassword: (email: string) =>
    apiClient.post<{ message: string }>('/auth/forgot-password', { email }),

  resetPassword: (token: string, newPassword: string) =>
    apiClient.post<{ message: string }>('/auth/reset-password', {
      token,
      new_password: newPassword,
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    apiClient.post<{ message: string }>('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  mfaSetup: () => apiClient.post<import('@/types/auth').MfaSetupResponse>('/auth/mfa/setup'),

  mfaVerify: (code: string, context = 'login') =>
    apiClient.post<{ message: string }>('/auth/mfa/verify', { code, context }),

  mfaEnable: (totpCode: string, pendingSecret: string) =>
    apiClient.post<{ message: string }>('/auth/mfa/enable', {
      totp_code: totpCode,
      pending_secret: pendingSecret,
    }),

  mfaDisable: (password: string) =>
    apiClient.post<{ message: string }>('/auth/mfa/disable', { password }),

  mfaRecovery: (recoveryCode: string) =>
    apiClient.post<{ message: string }>('/auth/mfa/recovery', {
      recovery_code: recoveryCode,
    }),
}

// ============================================================
// User API
// ============================================================

export const userApi = {
  me: () => apiClient.get<import('@/types/auth').CurrentUser>('/users/me'),

  updateProfile: (data: Partial<import('@/types/auth').UserProfile>) =>
    apiClient.patch<import('@/types/auth').CurrentUser>('/users/me', data),

  security: () =>
    apiClient.get<import('@/types/auth').SecurityDashboard>('/users/me/security'),
}

export { axiosInstance as axios }
