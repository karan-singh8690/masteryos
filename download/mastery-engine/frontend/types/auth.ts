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
  mfaEnabled: boolean
  emailVerifiedAt: ISO8601 | null
  createdAt: ISO8601
}

export interface UserProfile {
  displayName: string
  timezone: string
  locale: string
  avatarUrl: string | null
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
  accessToken: string
  refreshToken: string | null
  expiresIn: number
  tokenType: string
  user: User
  requiresMfa?: boolean
  mfaSessionToken?: string
}

export interface LoginRequest {
  email: EmailAddress
  password: string
  mfaCode?: string
  recoveryCode?: string
}

export interface RegisterRequest {
  email: EmailAddress
  password: string
  displayName: string
  timezone?: string
  locale?: string
}

export interface RefreshRequest {
  refreshToken: string
}

export interface VerifyEmailRequest {
  token: string
}

export interface ForgotPasswordRequest {
  email: EmailAddress
}

export interface ResetPasswordRequest {
  token: string
  newPassword: string
}

export interface ChangePasswordRequest {
  currentPassword: string
  newPassword: string
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
