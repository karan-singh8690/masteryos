/**
 * User + authentication types.
 */

import type {
  EmailAddress,
  ISO8601,
  NotificationChannel,
  NotificationPriority,
  UserRole,
  UserStatus,
  UUID,
} from './common'

export interface User {
  id: UUID
  email: EmailAddress
  status: UserStatus
  mfa_enabled: boolean
  email_verified_at: ISO8601 | null
  created_at: ISO8601
}

export interface UserProfile {
  display_name: string
  timezone: string
  locale: string
  avatar_url: string | null
  preferences: Record<string, unknown>
}

export interface CurrentUser {
  user: User
  profile: UserProfile
  roles: UserRole[]
  permissions: string[]
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface AuthResponse {
  access_token: string
  refresh_token: string | null
  expires_in: number
  token_type: string
  user: User
  requires_mfa?: boolean
  mfa_session_token?: string
}

export interface LoginRequest {
  email: EmailAddress
  password: string
  mfa_code?: string
  mfa_session_token?: string
  recovery_code?: string
}

export interface RegisterRequest {
  email: EmailAddress
  password: string
  display_name: string
  invite_token?: string
  timezone?: string
  locale?: string
}

export interface RefreshRequest {
  refresh_token: string
}

export interface VerifyEmailRequest {
  token: string
}

export interface ForgotPasswordRequest {
  email: EmailAddress
}

export interface ResetPasswordRequest {
  token: string
  new_password: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface MfaSetupResponse {
  secret: string
  qrCodeUri: string
  recoveryCodes: string[]
}

export interface MfaEnableRequest {
  totpCode: string
  pendingSecret: string
}

export interface MfaVerifyRequest {
  code: string
  context?: string
}

export interface MfaDisableRequest {
  password: string
}

export interface MfaRecoveryRequest {
  recoveryCode: string
}

export interface Session {
  id: UUID
  deviceFingerprint: string | null
  lastIp: string | null
  userAgent: string | null
  expiresAt: ISO8601
  lastSeenAt: ISO8601
  createdAt: ISO8601
  isCurrent?: boolean
}

export interface SecurityDashboard {
  mfaEnabled: boolean
  emailVerified: boolean
  passwordLastChangedAt: ISO8601 | null
  activeSessions: Session[]
  recoveryCodesRemaining: number
  recentSecurityEvents: SecurityEvent[]
}

export interface SecurityEvent {
  action: string
  success: boolean
  ipAddress: string | null
  createdAt: ISO8601
}

export interface Notification {
  id: UUID
  userId: UUID
  notificationType: string
  channel: NotificationChannel
  priority: NotificationPriority
  status: 'queued' | 'sent' | 'delivered' | 'opened' | 'dismissed' | 'failed'
  title: string
  body: string
  payload: Record<string, unknown>
  scheduledAt: ISO8601
  sentAt: ISO8601 | null
  deliveredAt: ISO8601 | null
  openedAt: ISO8601 | null
  dismissedAt: ISO8601 | null
  createdAt: ISO8601
}

export interface NotificationPreferences {
  emailEnabled: boolean
  inAppEnabled: boolean
  pushEnabled: boolean
  smsEnabled: boolean
  securityNotificationsEnabled: boolean
  achievementNotificationsEnabled: boolean
  marketingNotificationsEnabled: boolean
  reminderNotificationsEnabled: boolean
  digestFrequency: 'immediate' | 'hourly' | 'daily' | 'weekly' | 'never'
  quietHoursStart: string | null
  quietHoursEnd: string | null
  timezone: string
}
