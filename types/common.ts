/**
 * Common shared types.
 */

export type UUID = string

export type ISO8601 = string

export type EmailAddress = string

export type Maybe<T> = T | null

export type Nullable<T> = T | null | undefined

export type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error }

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasNext: boolean
  hasPrev: boolean
}

export interface PaginationParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface ApiErrorResponse {
  detail: {
    code: string
    message: string
    fields?: Record<string, string[]>
  }
}

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'
export type NotificationChannel = 'in_app' | 'email' | 'push' | 'sms'
export type NotificationStatus = 'queued' | 'sent' | 'delivered' | 'opened' | 'dismissed' | 'failed'

export type UserRole =
  | 'learner'
  | 'instructor'
  | 'content_editor'
  | 'organization_admin'
  | 'administrator'
  | 'system_admin'

export type UserStatus =
  | 'pending_verification'
  | 'active'
  | 'suspended'
  | 'deactivated'
  | 'pending_deletion'
  | 'anonymized'
