/**
 * Application constants.
 */

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'Mastery Engine'
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const API_VERSION = 'v1'
export const API_BASE_URL = `${API_URL}/api/${API_VERSION}`

export const TOKEN_STORAGE_KEY = 'mastery.access_token'
export const REFRESH_TOKEN_STORAGE_KEY = 'mastery.refresh_token'
export const THEME_STORAGE_KEY = 'mastery.theme'

export const ACCESS_TOKEN_EXPIRY_SECONDS = 15 * 60 // 15 minutes
export const REFRESH_TOKEN_EXPIRY_DAYS = 30

export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

export const PASSWORD_MIN_LENGTH = 12
export const PASSWORD_MAX_LENGTH = 128

export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  VERIFY_EMAIL: '/verify-email',
  MFA_SETUP: '/mfa/setup',
  MFA_VERIFY: '/mfa/verify',
  RECOVERY_CODES: '/recovery-codes',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  SECURITY: '/security',
  SETTINGS: '/settings',
  NOTIFICATIONS: '/notifications',
  UNAUTHORIZED: '/unauthorized',
  FORBIDDEN: '/forbidden',
  SESSION_EXPIRED: '/session-expired',
  OFFLINE: '/offline',
  MAINTENANCE: '/maintenance',
} as const

export const API_ROUTES = {
  AUTH: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    LOGOUT_ALL: '/auth/logout-all',
    VERIFY_EMAIL: '/auth/verify-email',
    RESEND_VERIFICATION: '/auth/resend-verification',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
    CHANGE_PASSWORD: '/auth/change-password',
    MFA_SETUP: '/auth/mfa/setup',
    MFA_VERIFY: '/auth/mfa/verify',
    MFA_ENABLE: '/auth/mfa/enable',
    MFA_DISABLE: '/auth/mfa/disable',
    MFA_RECOVERY: '/auth/mfa/recovery',
  },
  USERS: {
    ME: '/users/me',
    SECURITY: '/users/me/security',
  },
} as const

export const NOTIFICATION_PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const
export const NOTIFICATION_CHANNELS = ['in_app', 'email', 'push', 'sms'] as const

export const USER_ROLES = [
  'learner',
  'instructor',
  'content_editor',
  'organization_admin',
  'administrator',
  'system_admin',
] as const

export const MFA_RECOVERY_CODE_COUNT = 10
